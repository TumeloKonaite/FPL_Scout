from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import CompletedReportRun, PipelineRun
from src.app.infrastructure.serialization import to_json_value
from src.schemas.report_identity import ReportIdentity


class ReportStoreError(Exception):
    pass


class ReportDirectoryNotFoundError(ReportStoreError, FileNotFoundError):
    """Compatibility alias: means the report relation has no matching rows."""


class EmptyReportDirectoryError(ReportStoreError, FileNotFoundError):
    """Compatibility alias: means the report relation has no matching rows."""


class ReportNotFoundError(ReportStoreError, FileNotFoundError):
    pass


class InvalidReportFileError(ReportStoreError, ValueError):
    """Compatibility alias: means a stored report snapshot is invalid."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportRepository:
    def __init__(
        self, session_factory: sessionmaker[Session] | None = None
    ) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save_snapshot(
        self,
        *,
        run_id: str,
        season: str,
        gameweek: int,
        discovered_videos: list,
        input_jobs: list,
        expert_outputs: list,
        failed_jobs: list,
        duplicate_sources: list,
        transcript_failures: list,
        aggregate_report: dict,
        final_report: dict,
        manifest: dict,
        rendered_markdown: str | None,
        pipeline_run_id: str | None = None,
    ) -> CompletedReportRun:
        identity = ReportIdentity(season, gameweek)
        now = _utc_now()
        with self._session_factory.begin() as session:
            pipeline = (
                session.get(PipelineRun, pipeline_run_id)
                if pipeline_run_id is not None
                else None
            )
            if pipeline_run_id is not None and pipeline is None:
                raise KeyError(f"Pipeline run not found: {pipeline_run_id}")
            record = session.get(CompletedReportRun, run_id)
            values = {
                "pipeline_run_id": pipeline_run_id,
                "season": identity.season,
                "gameweek": identity.gameweek,
                "status": "processing" if pipeline is not None else "completed",
                "discovered_videos": to_json_value(discovered_videos),
                "input_jobs": to_json_value(input_jobs),
                "expert_outputs": to_json_value(expert_outputs),
                "failed_jobs": to_json_value(failed_jobs),
                "duplicate_sources": to_json_value(duplicate_sources),
                "transcript_failures": to_json_value(transcript_failures),
                "aggregate_report": to_json_value(aggregate_report),
                "final_report": to_json_value(final_report),
                "manifest": to_json_value(
                    {
                        **manifest,
                        "status": (
                            "processing" if pipeline is not None else "completed"
                        ),
                    }
                ),
                "rendered_markdown": to_json_value(rendered_markdown),
                "updated_at": now,
                "completed_at": None if pipeline is not None else now,
            }
            if record is None:
                record = CompletedReportRun(
                    run_id=run_id, created_at=now, **values
                )
                session.add(record)
            else:
                for name, value in values.items():
                    setattr(record, name, value)
            session.flush()
            return record

    def list_reports(self, *, completed_only: bool = True) -> list[CompletedReportRun]:
        with self._session_factory() as session:
            statement = select(CompletedReportRun)
            if completed_only:
                statement = statement.where(CompletedReportRun.status == "completed")
            return list(
                session.scalars(
                    statement.order_by(
                        CompletedReportRun.updated_at,
                        CompletedReportRun.run_id,
                    )
                )
            )

    def get(self, run_id: str) -> CompletedReportRun:
        with self._session_factory() as session:
            record = session.get(CompletedReportRun, run_id)
            if record is None:
                raise ReportNotFoundError(f"Report not found: {run_id}")
            return record

    def completed_for_gameweek(
        self, season: str, gameweek: int
    ) -> list[CompletedReportRun]:
        identity = ReportIdentity(season, gameweek)
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(CompletedReportRun)
                    .where(
                        CompletedReportRun.season == identity.season,
                        CompletedReportRun.gameweek == identity.gameweek,
                        CompletedReportRun.status == "completed",
                    )
                    .order_by(
                        CompletedReportRun.updated_at,
                        CompletedReportRun.run_id,
                    )
                )
            )

    def latest_completed(
        self, season: str | None = None, gameweek: int | None = None
    ) -> CompletedReportRun:
        statement = select(CompletedReportRun).where(
            CompletedReportRun.status == "completed"
        )
        if (season is None) != (gameweek is None):
            raise ValueError("season and gameweek must be provided together")
        if season is not None and gameweek is not None:
            identity = ReportIdentity(season, gameweek)
            statement = statement.where(
                CompletedReportRun.season == identity.season,
                CompletedReportRun.gameweek == identity.gameweek,
            )
        statement = statement.order_by(
            CompletedReportRun.updated_at.desc(),
            CompletedReportRun.run_id.desc(),
        ).limit(1)
        with self._session_factory() as session:
            record = session.scalar(statement)
            if record is None:
                raise EmptyReportDirectoryError("No completed reports were found")
            return record
