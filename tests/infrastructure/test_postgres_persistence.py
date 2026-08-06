from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from src.app.core.config import Settings
from src.app.domain.reports.service import ReportService
from src.app.infrastructure.models import Base, CompletedReportRun
from src.app.infrastructure.pipeline_run_repository import (
    ActivePipelineRunError,
    PipelineRunRepository,
)
from src.app.infrastructure.report_repository import (
    ImmutableReportSnapshotError,
    ReportRepository,
)
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

    assert (
        PipelineRunRepository(postgres_session_factory).get("run-1")["status"]
        == "completed"
    )
    assert [
        row.run_id
        for row in ReportRepository(postgres_session_factory).list_reports(
            completed_only=True
        )
    ] == ["run-1"]


def test_report_snapshot_removes_postgres_unsupported_null_characters(
    postgres_session_factory,
) -> None:
    reports = ReportRepository(postgres_session_factory)

    reports.save_snapshot(
        run_id="run-null-character",
        season="2025-26",
        gameweek=1,
        discovered_videos=[{"title": "14 VALUE Players for Gameweek 1 \x00"}],
        input_jobs=[{"video_title": "Title \x00"}],
        expert_outputs=[{"video_title": "Title \x00"}],
        failed_jobs=[],
        duplicate_sources=[],
        transcript_failures=[],
        aggregate_report={
            "season": "2025-26",
            "gameweek": 1,
            "nested": {"value": "Aggregate \x00"},
        },
        final_report={
            "season": "2025-26",
            "gameweek": 1,
            "overview": "Final \x00",
        },
        manifest={"source\x00": "Manifest \x00"},
        rendered_markdown="# GW1 \x00",
    )

    stored = reports.get("run-null-character")
    assert stored.discovered_videos[0]["title"] == ("14 VALUE Players for Gameweek 1 ")
    assert stored.input_jobs[0]["video_title"] == "Title "
    assert stored.expert_outputs[0]["video_title"] == "Title "
    assert stored.aggregate_report["nested"]["value"] == "Aggregate "
    assert stored.final_report["overview"] == "Final "
    assert stored.manifest["source"] == "Manifest "
    assert stored.rendered_markdown == "# GW1 "


def test_public_recommendation_selects_latest_completed_report_in_postgres(
    postgres_session_factory,
) -> None:
    reports = ReportRepository(postgres_session_factory)
    common = {
        "season": "2025-26",
        "gameweek": 32,
        "discovered_videos": [],
        "input_jobs": [],
        "expert_outputs": [{"unused": "x" * 100_000}],
        "failed_jobs": [],
        "duplicate_sources": [],
        "transcript_failures": [],
        "aggregate_report": {"malformed": "x" * 100_000},
        "final_report": {
            "season": "2025-26",
            "gameweek": 32,
            "overview": "Selected report",
            "conclusion": "Conclusion",
        },
        "manifest": {"unused": "x" * 100_000},
        "rendered_markdown": None,
    }
    reports.save_snapshot(run_id="run-old", **common)
    reports.save_snapshot(run_id="run-a", **common)
    reports.save_snapshot(run_id="run-b", **common)
    reports.save_snapshot(
        run_id="run-z-processing", initial_status="processing", **common
    )
    oldest = datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc)
    tied = datetime(2026, 8, 6, 11, 0, tzinfo=timezone.utc)
    newest = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    with postgres_session_factory.begin() as session:
        session.get(CompletedReportRun, "run-old").updated_at = oldest
        session.get(CompletedReportRun, "run-a").updated_at = tied
        session.get(CompletedReportRun, "run-b").updated_at = tied
        session.get(CompletedReportRun, "run-z-processing").updated_at = newest

    record = reports.latest_public_recommendation("2025-26", 32)
    public_report = ReportService(reports).get_public_recommendation("2025-26", 32)

    assert record is not None
    assert record.run_id == "run-b"
    assert public_report.run_id == "run-b"
    assert public_report.final_report.overview == "Selected report"
    assert public_report.aggregate_report is None


def test_completed_report_snapshot_cannot_be_overwritten(
    postgres_session_factory,
) -> None:
    reports = ReportRepository(postgres_session_factory)
    values = {
        "run_id": "immutable-run",
        "season": "2025-26",
        "gameweek": 1,
        "discovered_videos": [],
        "input_jobs": [],
        "expert_outputs": [],
        "failed_jobs": [],
        "duplicate_sources": [],
        "transcript_failures": [],
        "aggregate_report": {"season": "2025-26", "gameweek": 1},
        "final_report": {"season": "2025-26", "gameweek": 1},
        "manifest": {},
        "rendered_markdown": None,
    }
    reports.save_snapshot(**values)

    with pytest.raises(ImmutableReportSnapshotError, match="immutable-run"):
        reports.save_snapshot(
            **{
                **values,
                "final_report": {"season": "2025-26", "gameweek": 1, "changed": True},
            }
        )

    assert "changed" not in reports.get("immutable-run").final_report


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


def test_replacement_publication_supersedes_previous_report_atomically(
    postgres_session_factory,
) -> None:
    reports = ReportRepository(postgres_session_factory)
    common = {
        "season": "2025-26",
        "gameweek": 30,
        "discovered_videos": [],
        "input_jobs": [],
        "expert_outputs": [],
        "failed_jobs": [],
        "duplicate_sources": [],
        "transcript_failures": [],
        "aggregate_report": {"season": "2025-26", "gameweek": 30},
        "final_report": {"season": "2025-26", "gameweek": 30},
        "rendered_markdown": None,
    }
    reports.save_snapshot(run_id="legacy", manifest={}, **common)
    reports.save_snapshot(
        run_id="replacement",
        manifest={
            "provenance_validation": [{"selected": True, "video_id": "abcdefghijk"}]
        },
        initial_status="processing",
        **common,
    )

    superseded = reports.publish_replacement(
        replacement_run_id="replacement",
        historical_deadline=datetime(2026, 3, 14, 13, 30, tzinfo=timezone.utc),
        batch_identifier="batch-1",
        command="regenerate",
        supersession_reason="contaminated historical sources",
        validation_rule_version="historical-provenance-v1",
        selected_video_fingerprint="fingerprint",
        audit_data={"validated": True},
    )

    legacy = reports.get("legacy")
    assert superseded == ["legacy"]
    assert legacy.status == "superseded"
    assert legacy.superseded_by_run_id == "replacement"
    assert legacy.superseded_at is not None
    assert legacy.supersession_reason == "contaminated historical sources"
    assert reports.latest_completed("2025-26", 30).run_id == "replacement"
    assert reports.list_reports()[-1].run_id == "replacement"
    assert reports.get("legacy").run_id == "legacy"
    audits = reports.list_regeneration_audits(batch_identifier="batch-1")
    assert len(audits) == 1
    assert audits[0].previous_run_id == "legacy"
    assert audits[0].replacement_run_id == "replacement"


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
        path.read_text(encoding="utf-8") for path in (root / "src").rglob("*.py")
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
