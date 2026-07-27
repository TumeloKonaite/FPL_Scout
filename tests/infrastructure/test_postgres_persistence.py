from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from src.app.core.config import Settings
from src.app.infrastructure.models import Base
from src.app.infrastructure.pipeline_run_repository import (
    ActivePipelineRunError,
    PipelineRunRepository,
)
from src.app.infrastructure.report_repository import ReportRepository
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.services import transcript_service


@pytest.fixture
def postgres_session_factory():
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL; SQLite is unsupported")
    if not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a dedicated *_test database")
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_pipeline_exclusivity_survives_repository_recreation(
    postgres_session_factory,
) -> None:
    first = PipelineRunRepository(postgres_session_factory)
    second = PipelineRunRepository(postgres_session_factory)
    first.create_if_idle("run-1", {"season": "2025-26", "gameweek": 1})

    with pytest.raises(ActivePipelineRunError, match="run-1"):
        second.create_if_idle("run-2", {"season": "2025-26", "gameweek": 2})

    assert second.get("run-1")["status"] == "queued"


def test_report_publish_and_terminal_run_update_are_atomic(
    postgres_session_factory,
) -> None:
    runs = PipelineRunRepository(postgres_session_factory)
    reports = ReportRepository(postgres_session_factory)
    runs.create_if_idle("run-1", {"season": "2025-26", "gameweek": 1})
    runs.update("run-1", "running")
    reports.save_snapshot(
        run_id="run-1",
        pipeline_run_id="run-1",
        season="2025-26",
        gameweek=1,
        discovered_videos=[],
        input_jobs=[],
        expert_outputs=[],
        failed_jobs=[],
        duplicate_sources=[],
        transcript_failures=[],
        aggregate_report={"season": "2025-26", "gameweek": 1},
        final_report={"season": "2025-26", "gameweek": 1},
        manifest={},
        rendered_markdown="# GW1",
    )

    assert reports.list_reports(completed_only=True) == []
    runs.complete_with_report("run-1", {"run_path": "run-1"})

    assert PipelineRunRepository(postgres_session_factory).get("run-1")[
        "status"
    ] == "completed"
    assert [
        row.run_id
        for row in ReportRepository(postgres_session_factory).list_reports(
            completed_only=True
        )
    ] == ["run-1"]


def test_failed_pipeline_invalidates_unpublished_report_atomically(
    postgres_session_factory,
) -> None:
    runs = PipelineRunRepository(postgres_session_factory)
    reports = ReportRepository(postgres_session_factory)
    runs.create_if_idle("run-failed", {"season": "2025-26", "gameweek": 2})
    runs.update("run-failed", "running")
    reports.save_snapshot(
        run_id="run-failed",
        pipeline_run_id="run-failed",
        season="2025-26",
        gameweek=2,
        discovered_videos=[],
        input_jobs=[],
        expert_outputs=[],
        failed_jobs=[],
        duplicate_sources=[],
        transcript_failures=[],
        aggregate_report={"season": "2025-26", "gameweek": 2},
        final_report={"season": "2025-26", "gameweek": 2},
        manifest={},
        rendered_markdown=None,
    )

    runs.fail_with_report("run-failed", "provider unavailable")

    assert runs.get("run-failed")["status"] == "failed"
    assert reports.get("run-failed").status == "invalid"
    assert reports.list_reports() == []


def test_transcript_revision_survives_repository_recreation(
    postgres_session_factory,
) -> None:
    first = TranscriptRepository(postgres_session_factory)
    saved = first.save_available(
        video_id="video-1", transcript_text=" Durable transcript "
    )

    second = TranscriptRepository(postgres_session_factory)
    reloaded = second.get_by_video_id("video-1")
    revisions = second.list_history(saved.id)

    assert reloaded is not None
    assert reloaded.transcript_text == "Durable transcript"
    assert len(revisions) == 1


def test_database_failure_never_falls_back_to_files(monkeypatch, tmp_path) -> None:
    class BrokenRepository:
        def get_by_video_id(self, video_id):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        transcript_service,
        "fetch_transcript",
        lambda *args, **kwargs: pytest.fail("provider should not be called"),
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        transcript_service.get_clean_transcript(
            "video-1", repository=BrokenRepository(), cache_dir=tmp_path
        )
    assert list(tmp_path.iterdir()) == []


def test_removed_storage_settings_are_ignored() -> None:
    settings = Settings(
        DATA_DIR="/tmp/legacy",
        REPORTS_DIR="/tmp/legacy/reports",
        TRANSCRIPT_FILE_FALLBACK_ENABLED=True,
        _env_file=None,
    )
    assert not hasattr(settings, "DATA_DIR")
    assert not hasattr(settings, "REPORTS_DIR")
    assert not hasattr(settings, "TRANSCRIPT_FILE_FALLBACK_ENABLED")


def test_application_has_no_filesystem_or_sqlite_persistence_paths() -> None:
    root = Path(__file__).resolve().parents[2]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src").rglob("*.py")
    )
    forbidden = (
        "sqlite://",
        "TRANSCRIPT_FILE_FALLBACK_ENABLED",
        "REPORTS_DIR",
        ".pipeline.lock",
        "index.json",
        "runtime_volume",
    )
    for marker in forbidden:
        assert marker not in source
