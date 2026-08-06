from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260806_06_add_report_publication_status.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "report_publication_status_migration", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_migration_declares_deterministic_backfill_before_unique_index() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ORDER BY updated_at DESC, created_at DESC, run_id DESC" in source
    assert source.index("WITH ranked AS") < source.index(
        '"uq_published_report_per_gameweek"'
    )
    assert "publication_status = 'published'" in source


def test_backfill_and_unique_index_in_postgres() -> None:
    database_url = os.getenv("TEST_DATABASE_URL", "")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL; SQLite is unsupported")
    if not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a dedicated *_test database")

    schema = f"publication_migration_{uuid4().hex}"
    engine = create_engine(database_url)
    migration = _load_migration()
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.execute(
                text(
                    """
                    CREATE TABLE completed_report_runs (
                        run_id varchar(64) PRIMARY KEY,
                        season varchar(7) NOT NULL,
                        gameweek integer NOT NULL,
                        status varchar(16) NOT NULL,
                        final_report jsonb NOT NULL,
                        created_at timestamptz NOT NULL,
                        updated_at timestamptz NOT NULL,
                        superseded_by_run_id varchar(64),
                        superseded_at timestamptz,
                        supersession_reason text,
                        CONSTRAINT ck_completed_report_runs_supersession_fields
                        CHECK (
                            (status = 'superseded'
                             AND superseded_by_run_id IS NOT NULL
                             AND superseded_at IS NOT NULL
                             AND supersession_reason IS NOT NULL)
                            OR
                            (status != 'superseded'
                             AND superseded_by_run_id IS NULL
                             AND superseded_at IS NULL
                             AND supersession_reason IS NULL)
                        )
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX ix_completed_report_runs_public_recommendation
                    ON completed_report_runs
                    (season, gameweek, updated_at DESC, run_id DESC)
                    WHERE status = 'completed' AND final_report IS NOT NULL
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX ix_completed_report_public_lookup
                    ON completed_report_runs
                    (season, gameweek, updated_at DESC)
                    WHERE status = 'completed'
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO completed_report_runs
                        (run_id, season, gameweek, status, final_report,
                         created_at, updated_at)
                    VALUES
                        ('only', '2025-26', 1, 'completed', '{}',
                         '2026-08-01T10:00:00Z', '2026-08-01T10:00:00Z'),
                        ('tie-a', '2025-26', 2, 'completed', '{}',
                         '2026-08-02T10:00:00Z', '2026-08-02T10:00:00Z'),
                        ('tie-b', '2025-26', 2, 'completed', '{}',
                         '2026-08-02T10:00:00Z', '2026-08-02T10:00:00Z'),
                        ('invalid', '2025-26', 3, 'invalid', '{}',
                         '2026-08-03T10:00:00Z', '2026-08-03T10:00:00Z')
                    """
                )
            )
            connection.commit()

            context = MigrationContext.configure(connection)
            with context.begin_transaction():
                with Operations.context(context):
                    migration.upgrade()

            states = dict(
                connection.execute(
                    text(
                        "SELECT run_id, publication_status "
                        "FROM completed_report_runs"
                    )
                ).all()
            )
            assert states == {
                "only": "published",
                "tie-a": "superseded",
                "tie-b": "published",
                "invalid": "unpublished",
            }
            index = connection.execute(
                text(
                    """
                    SELECT indexdef FROM pg_indexes
                    WHERE schemaname = :schema
                      AND indexname = 'uq_published_report_per_gameweek'
                    """
                ),
                {"schema": schema},
            ).scalar_one()
            assert "UNIQUE INDEX" in index
            assert "WHERE" in index
            assert "publication_status" in index
            assert "'published'" in index
    finally:
        with engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
