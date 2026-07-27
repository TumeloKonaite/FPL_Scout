from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import CompletedReportRun, PipelineRun

PipelineRunStatus = Literal["queued", "running", "completed", "failed"]
ACTIVE_STATUSES = ("queued", "running")


class ActivePipelineRunError(RuntimeError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Pipeline run {run_id} is already active")
        self.run_id = run_id


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
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "duration_seconds": record.duration_seconds,
    }


class PipelineRunRepository:
    """PostgreSQL-backed run state with database-enforced global exclusivity."""

    def __init__(
        self, session_factory: sessionmaker[Session] | None = None
    ) -> None:
        self._session_factory = session_factory or get_session_factory()

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
        )
        try:
            with self._session_factory.begin() as session:
                session.add(record)
                session.flush()
                payload = _as_dict(record)
        except IntegrityError as exc:
            active = self.get_active()
            if active is not None:
                raise ActivePipelineRunError(active["run_id"]) from exc
            raise
        return payload

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
            self._transition(
                record,
                status,
                result=result,
                error=error,
                current_stage=current_stage,
            )
            session.flush()
            return _as_dict(record)

    def complete_with_report(
        self, run_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Publish the report snapshot and complete its pipeline run atomically."""
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(PipelineRun)
                .where(PipelineRun.run_id == run_id)
                .with_for_update()
            )
            if record is None:
                raise KeyError(f"Pipeline run not found: {run_id}")
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
                "updated_at": now.isoformat(),
            }
            self._transition(record, "completed", result=result, now=now)
            session.flush()
            return _as_dict(record)

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
            report = session.scalar(
                select(CompletedReportRun)
                .where(CompletedReportRun.pipeline_run_id == run_id)
                .with_for_update()
            )
            now = _utc_now()
            if report is not None and report.status == "processing":
                report.status = "invalid"
                report.updated_at = now
                report.manifest = {
                    **report.manifest,
                    "status": "invalid",
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
        if status == "running":
            record.started_at = record.started_at or now
            record.current_stage = current_stage or "analysis"
        elif status in {"completed", "failed"}:
            record.completed_at = now
            record.current_stage = None
            started = record.started_at or record.created_at
            record.duration_seconds = max(0.0, (now - started).total_seconds())
        elif current_stage is not None:
            record.current_stage = current_stage
