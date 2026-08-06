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
    / "20260806_05_add_completed_report_public_lookup_index.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "completed_report_public_lookup_migration", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


class _RecordingContext:
    def __init__(self) -> None:
        self.autocommit_depth = 0
        self.autocommit_entries = 0

    def autocommit_block(self) -> _RecordingContext:
        return self

    def __enter__(self) -> None:
        self.autocommit_depth += 1
        self.autocommit_entries += 1

    def __exit__(self, *args: object) -> None:
        self.autocommit_depth -= 1


class _RecordingOperations:
    def __init__(self) -> None:
        self.context = _RecordingContext()
        self.statements: list[str] = []

    def get_context(self) -> _RecordingContext:
        return self.context

    def execute(self, statement: str) -> None:
        assert self.context.autocommit_depth == 1
        self.statements.append(" ".join(statement.split()))


@pytest.fixture
def migration_and_operations(monkeypatch):
    migration = _load_migration()
    operations = _RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)
    return migration, operations


def test_upgrade_creates_the_requested_partial_composite_index(
    migration_and_operations,
) -> None:
    migration, operations = migration_and_operations

    migration.upgrade()

    assert operations.statements == [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_completed_report_public_lookup ON completed_report_runs "
        "( season, gameweek, updated_at DESC ) WHERE status = 'completed'"
    ]


def test_upgrade_is_idempotent_when_the_index_already_exists(
    migration_and_operations,
) -> None:
    migration, operations = migration_and_operations

    migration.upgrade()
    migration.upgrade()

    assert len(operations.statements) == 2
    assert all(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS" in sql
        for sql in operations.statements
    )


def test_downgrade_removes_the_index_concurrently(migration_and_operations) -> None:
    migration, operations = migration_and_operations

    migration.downgrade()

    assert operations.statements == [
        "DROP INDEX CONCURRENTLY IF EXISTS ix_completed_report_public_lookup"
    ]


def test_downgrade_is_idempotent_when_the_index_is_absent(
    migration_and_operations,
) -> None:
    migration, operations = migration_and_operations

    migration.downgrade()
    migration.downgrade()

    assert len(operations.statements) == 2
    assert all(
        "DROP INDEX CONCURRENTLY IF EXISTS" in sql for sql in operations.statements
    )


def test_concurrent_ddl_runs_in_an_autocommit_block(
    migration_and_operations,
) -> None:
    migration, operations = migration_and_operations

    migration.upgrade()
    migration.downgrade()

    assert operations.context.autocommit_entries == 2


def test_migration_is_reversible_and_idempotent_in_postgres() -> None:
    database_url = os.getenv("TEST_DATABASE_URL", "")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL; SQLite is unsupported")
    if not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a dedicated *_test database")

    migration = _load_migration()
    schema = f"migration_index_{uuid4().hex}"
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.execute(
                text(
                    """
                    CREATE TABLE completed_report_runs (
                        season text NOT NULL,
                        gameweek integer NOT NULL,
                        updated_at timestamptz NOT NULL,
                        status text NOT NULL
                    )
                    """
                )
            )
            connection.commit()
            context = MigrationContext.configure(connection)
            with context.begin_transaction():
                with Operations.context(context):
                    migration.upgrade()
                    migration.upgrade()

                    indexes = (
                        connection.execute(
                            text(
                                """
                            SELECT indexdef
                            FROM pg_indexes
                            WHERE schemaname = :schema
                              AND indexname = 'ix_completed_report_public_lookup'
                            """
                            ),
                            {"schema": schema},
                        )
                        .scalars()
                        .all()
                    )
                    assert len(indexes) == 1
                    assert "(season, gameweek, updated_at DESC)" in indexes[0]
                    assert "WHERE (status = 'completed'::text)" in indexes[0]

                    migration.downgrade()
                    migration.downgrade()

                    assert (
                        connection.execute(
                            text(
                                """
                            SELECT count(*)
                            FROM pg_indexes
                            WHERE schemaname = :schema
                              AND indexname = 'ix_completed_report_public_lookup'
                            """
                            ),
                            {"schema": schema},
                        ).scalar_one()
                        == 0
                    )
    finally:
        with engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
