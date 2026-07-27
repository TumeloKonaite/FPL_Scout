from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.app.infrastructure.report_repository import ReportRepository
from src.app.infrastructure.serialization import to_json_value
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.schemas.report_identity import ReportIdentity
from src.services.report_formatter_service import format_gameweek_markdown_report


class ReportService:
    """Persist immutable, point-in-time report snapshots in PostgreSQL."""

    def __init__(
        self,
        repository: ReportRepository | None = None,
        *,
        pipeline_run_id: str | None = None,
    ) -> None:
        self.repository = repository or ReportRepository()
        self.pipeline_run_id = pipeline_run_id

    def persist_run(
        self,
        *,
        discovered_videos: list[Any] | None = None,
        input_jobs: list[Any],
        expert_outputs: list[Any],
        aggregate_report: Any,
        final_report: Any,
        failed_jobs: list[Any] | None = None,
        duplicate_sources: list[Any] | None = None,
        input_mode: str = "youtube_auto",
        configured_experts: int | None = None,
        videos_discovered: int | None = None,
        videos_selected: int | None = None,
        jobs_created: int | None = None,
        transcript_failures: list[Any] | None = None,
        run_id: str | None = None,
    ) -> str:
        aggregate = AggregatedFPLReport.model_validate(aggregate_report)
        final = FinalGameweekReport.model_validate(final_report)
        identity = ReportIdentity(final.season, final.gameweek)
        if (aggregate.season, aggregate.gameweek) != (
            identity.season,
            identity.gameweek,
        ):
            raise ValueError(
                "aggregate and final reports must have the same season and gameweek"
            )
        resolved_run_id = run_id or self.pipeline_run_id
        resolved_run_id = resolved_run_id or str(uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        failed = to_json_value(failed_jobs or [])
        duplicates = to_json_value(duplicate_sources or [])
        transcript_failure_values = to_json_value(transcript_failures or [])
        jobs = to_json_value(input_jobs)
        outputs = to_json_value(expert_outputs)
        discovered = to_json_value(discovered_videos or [])
        aggregate_value = to_json_value(aggregate)
        final_value = to_json_value(final)
        manifest = {
            "run_id": resolved_run_id,
            "created_at": now,
            "updated_at": now,
            "status": "completed",
            "season": identity.season,
            "gameweek": identity.gameweek,
            "input_mode": input_mode,
            "configured_experts": configured_experts or 0,
            "videos_discovered": (
                videos_discovered if videos_discovered is not None else len(discovered)
            ),
            "videos_selected": (
                videos_selected if videos_selected is not None else len(jobs)
            ),
            "jobs_created": jobs_created if jobs_created is not None else len(jobs),
            "counts": {
                "expert_outputs": len(outputs),
                "failed_jobs": len(failed),
                "input_jobs": len(jobs),
                "duplicate_sources": len(duplicates),
                "transcript_failures": len(transcript_failure_values),
            },
            "duplicate_sources": duplicates,
            "failed_jobs": failed,
            "transcript_failures": transcript_failure_values,
        }
        self.repository.save_snapshot(
            run_id=resolved_run_id,
            pipeline_run_id=self.pipeline_run_id,
            season=identity.season,
            gameweek=identity.gameweek,
            discovered_videos=discovered,
            input_jobs=jobs,
            expert_outputs=outputs,
            failed_jobs=failed,
            duplicate_sources=duplicates,
            transcript_failures=transcript_failure_values,
            aggregate_report=aggregate_value,
            final_report=final_value,
            manifest=to_json_value(manifest),
            rendered_markdown=to_json_value(
                format_gameweek_markdown_report(aggregate, final)
            ),
        )
        return resolved_run_id

    def load_run(self, run_id: str) -> dict[str, Any]:
        record = self.repository.get(run_id)
        return {
            "run_id": record.run_id,
            "manifest": record.manifest,
            "discovered_videos": record.discovered_videos,
            "input_jobs": record.input_jobs,
            "expert_outputs": record.expert_outputs,
            "aggregate_report": record.aggregate_report,
            "final_report": record.final_report,
            "report_markdown": record.rendered_markdown,
        }


def persist_run(**kwargs: Any) -> str:
    return ReportService().persist_run(**kwargs)


def load_run(run_id: str) -> dict[str, Any]:
    return ReportService().load_run(run_id)
