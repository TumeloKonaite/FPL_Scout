from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import (
    CompletedReportRun,
    HistoricalRegenerationAudit,
    PipelineRun,
)
from src.app.infrastructure.serialization import to_json_value
from src.app.core.public_recommendation_timing import measure
from src.schemas.report_identity import ReportIdentity


class ReportStoreError(Exception):
    pass


class ReportDirectoryNotFoundError(ReportStoreError, FileNotFoundError):
    """Compatibility alias: means the report relation has no matching rows."""


class EmptyReportDirectoryError(ReportStoreError, FileNotFoundError):
    """Compatibility alias: means the report relation has no matching rows."""


class ReportNotFoundError(ReportStoreError, FileNotFoundError):
    pass


class ImmutableReportSnapshotError(ReportStoreError):
    """Raised when a terminal report snapshot would be overwritten."""


class InvalidReportFileError(ReportStoreError, ValueError):
    """Compatibility alias: means a stored report snapshot is invalid."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PublicRecommendationRecord:
    """The only stored fields needed to serve a public recommendation."""

    run_id: str
    final_report: dict[str, Any]
    updated_at: datetime


class ReportRepository:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
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
        initial_status: str | None = None,
    ) -> CompletedReportRun:
        identity = ReportIdentity(season, gameweek)
        now = _utc_now()
        resolved_status = initial_status or (
            "processing" if pipeline_run_id is not None else "completed"
        )
        if resolved_status not in {"processing", "completed"}:
            raise ValueError("initial_status must be processing or completed")
        with self._session_factory.begin() as session:
            pipeline = (
                session.get(PipelineRun, pipeline_run_id)
                if pipeline_run_id is not None
                else None
            )
            if pipeline_run_id is not None and pipeline is None:
                raise KeyError(f"Pipeline run not found: {pipeline_run_id}")
            record = session.get(CompletedReportRun, run_id)
            if record is not None and record.status in {
                "completed",
                "superseded",
            }:
                raise ImmutableReportSnapshotError(
                    f"Completed report snapshot cannot be overwritten: {run_id}"
                )
            values = {
                "pipeline_run_id": pipeline_run_id,
                "season": identity.season,
                "gameweek": identity.gameweek,
                "status": resolved_status,
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
                        "status": resolved_status,
                    }
                ),
                "rendered_markdown": to_json_value(rendered_markdown),
                "updated_at": now,
                "completed_at": now if resolved_status == "completed" else None,
                "superseded_by_run_id": None,
                "superseded_at": None,
                "supersession_reason": None,
            }
            if record is None:
                record = CompletedReportRun(run_id=run_id, created_at=now, **values)
                session.add(record)
            else:
                for name, value in values.items():
                    setattr(record, name, value)
            session.flush()
            return record

    def reports_for_range(
        self,
        season: str,
        from_gameweek: int,
        to_gameweek: int,
        *,
        statuses: tuple[str, ...] | None = None,
    ) -> list[CompletedReportRun]:
        validate_from = ReportIdentity(season, from_gameweek)
        validate_to = ReportIdentity(season, to_gameweek)
        if validate_from.season != validate_to.season:
            raise ValueError("range must use one season")
        if from_gameweek > to_gameweek:
            raise ValueError("from_gameweek must not exceed to_gameweek")
        statement = select(CompletedReportRun).where(
            CompletedReportRun.season == validate_from.season,
            CompletedReportRun.gameweek.between(from_gameweek, to_gameweek),
        )
        if statuses is not None:
            statement = statement.where(CompletedReportRun.status.in_(statuses))
        with self._session_factory() as session:
            return list(
                session.scalars(
                    statement.order_by(
                        CompletedReportRun.gameweek,
                        CompletedReportRun.updated_at,
                        CompletedReportRun.run_id,
                    )
                )
            )

    def publish_replacement(
        self,
        *,
        replacement_run_id: str,
        historical_deadline: datetime,
        batch_identifier: str,
        command: str,
        supersession_reason: str,
        validation_rule_version: str,
        selected_video_fingerprint: str,
        audit_data: dict[str, Any],
    ) -> list[str]:
        """Publish a validated replacement and supersede prior canonicals atomically."""
        now = _utc_now()
        with self._session_factory.begin() as session:
            replacement = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.run_id == replacement_run_id)
                .with_for_update()
            )
            if replacement is None:
                raise ReportNotFoundError(f"Report not found: {replacement_run_id}")
            if replacement.status != "processing":
                raise ValueError("replacement report must be processing")

            # Serialize publishers for one season/gameweek even when there are
            # currently no report rows to lock.
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                {
                    "identity": (
                        f"historical-report:{replacement.season}:{replacement.gameweek}"
                    )
                },
            )
            prior = list(
                session.scalars(
                    select(CompletedReportRun)
                    .where(
                        CompletedReportRun.season == replacement.season,
                        CompletedReportRun.gameweek == replacement.gameweek,
                        CompletedReportRun.status == "completed",
                        CompletedReportRun.run_id != replacement.run_id,
                    )
                    .order_by(
                        CompletedReportRun.updated_at,
                        CompletedReportRun.run_id,
                    )
                    .with_for_update()
                )
            )
            replacement.status = "completed"
            replacement.completed_at = now
            replacement.updated_at = now
            replacement.manifest = {
                **replacement.manifest,
                "status": "completed",
                "updated_at": now.isoformat(),
                "regeneration": {
                    **dict(replacement.manifest.get("regeneration", {})),
                    "batch_identifier": batch_identifier,
                    "historical_deadline": historical_deadline.isoformat(),
                    "selected_video_fingerprint": selected_video_fingerprint,
                    "validation_rule_version": validation_rule_version,
                    "published_at": now.isoformat(),
                },
            }
            for previous in prior:
                if (
                    previous.season != replacement.season
                    or previous.gameweek != replacement.gameweek
                ):
                    raise ValueError(
                        "cross-season or cross-gameweek supersession is forbidden"
                    )
                previous.status = "superseded"
                previous.superseded_by_run_id = replacement.run_id
                previous.superseded_at = now
                previous.supersession_reason = supersession_reason
                previous.updated_at = now
                previous.manifest = {
                    **previous.manifest,
                    "status": "superseded",
                    "updated_at": now.isoformat(),
                    "superseded_by_run_id": replacement.run_id,
                    "superseded_at": now.isoformat(),
                    "supersession_reason": supersession_reason,
                }

            audit_rows = prior or [None]
            for previous in audit_rows:
                session.add(
                    HistoricalRegenerationAudit(
                        season=replacement.season,
                        gameweek=replacement.gameweek,
                        previous_run_id=previous.run_id if previous else None,
                        replacement_run_id=replacement.run_id,
                        previous_status="completed" if previous else None,
                        replacement_status="completed",
                        historical_deadline=historical_deadline,
                        selected_video_fingerprint=selected_video_fingerprint,
                        validation_rule_version=validation_rule_version,
                        batch_identifier=batch_identifier,
                        command=command,
                        audit_data=to_json_value(audit_data),
                        generated_at=now,
                        superseded_at=now if previous else None,
                    )
                )
            session.flush()
            canonical_ids = list(
                session.scalars(
                    select(CompletedReportRun.run_id).where(
                        CompletedReportRun.season == replacement.season,
                        CompletedReportRun.gameweek == replacement.gameweek,
                        CompletedReportRun.status == "completed",
                    )
                )
            )
            if canonical_ids != [replacement.run_id]:
                raise RuntimeError(
                    "Atomic publication did not produce exactly one canonical report"
                )
            return [row.run_id for row in prior]

    def invalidate_processing(self, run_id: str, reason: str) -> None:
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.run_id == run_id)
                .with_for_update()
            )
            if record is None:
                raise ReportNotFoundError(f"Report not found: {run_id}")
            if record.status != "processing":
                raise ValueError("only a processing report can be invalidated")
            now = _utc_now()
            record.status = "invalid"
            record.updated_at = now
            record.manifest = {
                **record.manifest,
                "status": "invalid",
                "updated_at": now.isoformat(),
                "invalidation_reason": reason,
            }

    def retract_replacement(self, run_id: str, reason: str) -> list[str]:
        """Compensate an erroneous publication while preserving its audit row."""
        now = _utc_now()
        with self._session_factory.begin() as session:
            replacement = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.run_id == run_id)
                .with_for_update()
            )
            if replacement is None:
                raise ReportNotFoundError(f"Report not found: {run_id}")
            if replacement.status != "completed":
                raise ValueError("only a completed replacement can be retracted")
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:identity))"),
                {
                    "identity": (
                        f"historical-report:{replacement.season}:{replacement.gameweek}"
                    )
                },
            )
            previous_rows = list(
                session.scalars(
                    select(CompletedReportRun)
                    .where(
                        CompletedReportRun.superseded_by_run_id == run_id,
                        CompletedReportRun.status == "superseded",
                    )
                    .with_for_update()
                )
            )
            replacement.status = "invalid"
            replacement.updated_at = now
            replacement.manifest = {
                **replacement.manifest,
                "status": "invalid",
                "updated_at": now.isoformat(),
                "retraction_reason": reason,
            }
            for previous in previous_rows:
                previous.status = "completed"
                previous.superseded_by_run_id = None
                previous.superseded_at = None
                previous.supersession_reason = None
                previous.updated_at = now
                previous.manifest = {
                    key: value
                    for key, value in previous.manifest.items()
                    if key
                    not in {
                        "superseded_by_run_id",
                        "superseded_at",
                        "supersession_reason",
                    }
                }
                previous.manifest = {
                    **previous.manifest,
                    "status": "completed",
                    "updated_at": now.isoformat(),
                }
            audits = list(
                session.scalars(
                    select(HistoricalRegenerationAudit)
                    .where(HistoricalRegenerationAudit.replacement_run_id == run_id)
                    .with_for_update()
                )
            )
            for audit in audits:
                audit.replacement_status = "invalid"
                audit.audit_data = {
                    **audit.audit_data,
                    "retracted_at": now.isoformat(),
                    "retraction_reason": reason,
                }
            session.flush()
            return [row.run_id for row in previous_rows]

    def list_regeneration_audits(
        self, *, batch_identifier: str | None = None
    ) -> list[HistoricalRegenerationAudit]:
        statement = select(HistoricalRegenerationAudit)
        if batch_identifier is not None:
            statement = statement.where(
                HistoricalRegenerationAudit.batch_identifier == batch_identifier
            )
        with self._session_factory() as session:
            return list(
                session.scalars(
                    statement.order_by(
                        HistoricalRegenerationAudit.generated_at,
                        HistoricalRegenerationAudit.gameweek,
                    )
                )
            )

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

    def latest_public_recommendation(
        self, season: str, gameweek: int
    ) -> PublicRecommendationRecord | None:
        """Load the newest publishable recommendation without pipeline payloads."""
        identity = ReportIdentity(season, gameweek)
        statement = (
            select(
                CompletedReportRun.run_id,
                CompletedReportRun.final_report,
                CompletedReportRun.updated_at,
            )
            .where(
                CompletedReportRun.season == identity.season,
                CompletedReportRun.gameweek == identity.gameweek,
                CompletedReportRun.status == "completed",
                CompletedReportRun.final_report.is_not(None),
            )
            .order_by(
                CompletedReportRun.updated_at.desc(),
                CompletedReportRun.run_id.desc(),
            )
            .limit(1)
        )
        with measure("db_session_ms", "db_session"):
            session = self._session_factory()
        with session:
            connection = getattr(session, "connection", None)
            if callable(connection):
                with measure("db_connection_wait_ms", "db_connection_acquisition"):
                    connection()
            with measure("db_query_ms", "db_query"):
                result = session.execute(statement)
            with measure("db_result_processing_ms", "db_result_processing"):
                row = result.one_or_none()
                if row is None:
                    return None
                return PublicRecommendationRecord(
                    run_id=row.run_id,
                    final_report=row.final_report,
                    updated_at=row.updated_at,
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
