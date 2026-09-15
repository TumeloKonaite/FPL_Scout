from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import CompletedReportRun, PipelineRun
from src.app.infrastructure.report_repository import ReportRepository

PipelineRunStatus = Literal["queued", "running", "completed", "failed"]
ACTIVE_STATUSES = ("queued", "running")
DEFAULT_LEASE_DURATION = timedelta(minutes=5)
DEFAULT_QUEUED_LEASE_DURATION = timedelta(minutes=15)
STALE_RUN_ERROR = "Pipeline run lease expired before the worker completed."


class ActivePipelineRunError(RuntimeError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Pipeline run {run_id} is already active")
        self.run_id = run_id


class InvalidPipelineRunTransition(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(record: PipelineRun) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "status": record.status,
        "result": record.result,
        "error": record.error,
        "input_data": record.input_data,
        "current_stage": record.current_stage,
        "created_at": record.created_at.isoformat(),
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "updated_at": record.updated_at.isoformat(),
        "heartbeat_at": record.heartbeat_at.isoformat() if record.heartbeat_at else None,
        "lease_expires_at": record.lease_expires_at.isoformat() if record.lease_expires_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "duration_seconds": record.duration_seconds,
    }


class PipelineRunRepository:
    """PostgreSQL-backed run state with database-enforced global exclusivity."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        lease_duration: timedelta = DEFAULT_LEASE_DURATION,
        queued_lease_duration: timedelta = DEFAULT_QUEUED_LEASE_DURATION,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._lease_duration = lease_duration
        self._queued_lease_duration = queued_lease_duration

    @property
    def heartbeat_interval_seconds(self) -> float:
        return max(1.0, min(60.0, self._lease_duration.total_seconds() / 3))

    def create(self, run_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.create_if_idle(run_id, input_data)

    def create_if_idle(
        self, run_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        now = _utc_now()
        record = PipelineRun(
            run_id=run_id,
            status="queued",
            current_stage="queued",
            input_data=input_data,
            created_at=now,
            updated_at=now,
            heartbeat_at=now,
            lease_expires_at=now + self._queued_lease_duration,
        )
        try:
            with self._session_factory.begin() as session:
                self._lock_active_runs(session)
                active = self._reconcile_stale_locked(session, now=now)
                if active is not None:
                    raise ActivePipelineRunError(active.run_id)
                session.add(record)
                session.flush()
                payload = _as_dict(record)
        except IntegrityError as exc:
            active = self.get_active()
            if active is not None:
                raise ActivePipelineRunError(active["run_id"]) from exc
            raise
        return payload

    def reconcile_stale(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Fail expired active records under the same lock used by run creation."""
        current = now or _utc_now()
        with self._session_factory.begin() as session:
            self._lock_active_runs(session)
            stale = self._reconcile_stale_locked(session, now=current, collect=True)
            session.flush()
            return [_as_dict(record) for record in stale]

    def heartbeat(self, run_id: str) -> dict[str, Any]:
        now = _utc_now()
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(PipelineRun).where(PipelineRun.run_id == run_id).with_for_update()
            )
            if record is None:
                raise KeyError(f"Pipeline run not found: {run_id}")
            if record.status not in ACTIVE_STATUSES:
                raise InvalidPipelineRunTransition(
                    f"Pipeline run {run_id} is already {record.status}"
                )
            record.heartbeat_at = now
            record.lease_expires_at = now + self._lease_duration
            record.updated_at = now
            session.flush()
            return _as_dict(record)

    def fail_active(self, run_id: str, reason: str) -> dict[str, Any]:
        """Administrator recovery action for a queued or running record."""
        return self.fail_with_report(run_id, reason)

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.get(PipelineRun, run_id)
            return _as_dict(record) if record is not None else None

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            records = session.scalars(
                select(PipelineRun)
                .order_by(PipelineRun.created_at.desc(), PipelineRun.run_id.desc())
                .limit(limit)
            ).all()
            return [_as_dict(record) for record in reversed(records)]

    def get_latest(self) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(PipelineRun)
                .order_by(PipelineRun.created_at.desc(), PipelineRun.run_id.desc())
                .limit(1)
            )
            return _as_dict(record) if record is not None else None

    def get_active(self) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.status.in_(ACTIVE_STATUSES))
                .order_by(PipelineRun.created_at.desc())
                .limit(1)
            )
            return _as_dict(record) if record is not None else None

    def update(
        self,
        run_id: str,
        status: PipelineRunStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        current_stage: str | None = None,
    ) -> dict[str, Any]:
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.run_id == run_id)
                .with_for_update()
            )
            if record is None:
                raise KeyError(f"Pipeline run not found: {run_id}")
            if record.status not in ACTIVE_STATUSES:
                raise InvalidPipelineRunTransition(
                    f"Pipeline run {run_id} is already {record.status}"
                )
            self._transition(
                record,
                status,
                result=result,
                error=error,
                current_stage=current_stage,
            )
            if status in ACTIVE_STATUSES:
                record.lease_expires_at = record.updated_at + self._lease_duration
            session.flush()
            return _as_dict(record)

    def complete_with_report(
        self, run_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Complete and publish a valid snapshot in one transaction."""
        with self._session_factory.begin() as session:
            report_identity = session.execute(
                select(CompletedReportRun.season, CompletedReportRun.gameweek).where(
                    CompletedReportRun.pipeline_run_id == run_id
                )
            ).one_or_none()
            if report_identity is None:
                raise RuntimeError(
                    f"Pipeline run {run_id} produced no persisted report snapshot"
                )
            ReportRepository._lock_publication_identity(
                session,
                season=report_identity.season,
                gameweek=report_identity.gameweek,
            )
            record = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.run_id == run_id)
                .with_for_update()
            )
            if record is None:
                raise KeyError(f"Pipeline run not found: {run_id}")
            if record.status != "running":
                raise InvalidPipelineRunTransition(
                    f"Pipeline run {run_id} cannot complete from {record.status}"
                )
            report = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.pipeline_run_id == run_id)
                .with_for_update()
            )
            if report is None:
                raise RuntimeError(
                    f"Pipeline run {run_id} produced no persisted report snapshot"
                )
            now = _utc_now()
            report.status = "completed"
            report.completed_at = now
            report.updated_at = now
            report.manifest = {
                **report.manifest,
                "status": "completed",
                "publication_status": "unpublished",
                "updated_at": now.isoformat(),
            }
            self._transition(record, "completed", result=result, now=now)
            ReportRepository._publish_locked(
                session,
                target=report,
                now=now,
                supersession_reason=f"Replaced by published report {report.run_id}",
            )
            session.flush()
            payload = _as_dict(record)
        return payload

    def fail_with_report(self, run_id: str, error: str) -> dict[str, Any]:
        """Fail a run and invalidate any unpublished report in one transaction."""
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.run_id == run_id)
                .with_for_update()
            )
            if record is None:
                raise KeyError(f"Pipeline run not found: {run_id}")
            if record.status == "failed":
                return _as_dict(record)
            if record.status not in ACTIVE_STATUSES:
                raise InvalidPipelineRunTransition(
                    f"Pipeline run {run_id} is already {record.status}"
                )
            report = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.pipeline_run_id == run_id)
                .with_for_update()
            )
            now = _utc_now()
            if report is not None and report.status == "processing":
                report.status = "invalid"
                report.publication_status = "unpublished"
                report.updated_at = now
                report.manifest = {
                    **report.manifest,
                    "status": "invalid",
                    "publication_status": "unpublished",
                    "updated_at": now.isoformat(),
                }
            self._transition(record, "failed", error=error, now=now)
            session.flush()
            return _as_dict(record)

    @staticmethod
    def _transition(
        record: PipelineRun,
        status: PipelineRunStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        current_stage: str | None = None,
        now: datetime | None = None,
    ) -> None:
        now = now or _utc_now()
        record.status = status
        record.result = result
        record.error = error
        record.updated_at = now
        if status in ACTIVE_STATUSES:
            record.heartbeat_at = now
        if status == "running":
            record.started_at = record.started_at or now
            record.current_stage = current_stage or "analysis"
        elif status in {"completed", "failed"}:
            record.lease_expires_at = None
            record.completed_at = now
            record.current_stage = None
            started = record.started_at or record.created_at
            record.duration_seconds = max(0.0, (now - started).total_seconds())
        elif current_stage is not None:
            record.current_stage = current_stage

    @staticmethod
    def _lock_active_runs(session: Session) -> None:
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext('pipeline-runs-active'))"))

    def _reconcile_stale_locked(
        self,
        session: Session,
        *,
        now: datetime,
        collect: bool = False,
    ) -> PipelineRun | list[PipelineRun] | None:
        records = list(
            session.scalars(
                select(PipelineRun)
                .where(PipelineRun.status.in_(ACTIVE_STATUSES))
                .order_by(PipelineRun.created_at)
                .with_for_update()
            )
        )
        stale: list[PipelineRun] = []
        live: PipelineRun | None = None
        for record in records:
            fallback_duration = (
                self._queued_lease_duration
                if record.status == "queued"
                else self._lease_duration
            )
            lease_expires_at = record.lease_expires_at or (
                record.updated_at + fallback_duration
            )
            if lease_expires_at <= now:
                self._transition(record, "failed", error=STALE_RUN_ERROR, now=now)
                report = session.scalar(
                    select(CompletedReportRun).where(
                        CompletedReportRun.pipeline_run_id == record.run_id
                    )
                )
                if report is not None and report.status == "processing":
                    report.status = "invalid"
                    report.publication_status = "unpublished"
                    report.updated_at = now
                    report.manifest = {
                        **report.manifest,
                        "status": "invalid",
                        "publication_status": "unpublished",
                        "updated_at": now.isoformat(),
                    }
                stale.append(record)
            else:
                live = record
        return stale if collect else live
