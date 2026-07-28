from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from threading import Thread
from typing import Any
from uuid import uuid4

from src.adapters.fpl import get_player_catalogue_provider
from src.adapters.transcript_api import (
    load_webshare_proxy_settings,
)
from src.app.infrastructure.pipeline_run_repository import PipelineRunRepository
from src.services.report_service import ReportService as ReportWriteService
from src.services.pipeline_service import (
    PipelineRunResult,
    run_pipeline_sync as execute_pipeline_sync,
)
from src.schemas.report_identity import validate_season

PipelineExecutor = Callable[..., PipelineRunResult]
PipelineDispatcher = Callable[[str, dict[str, Any]], None]


def _pipeline_result_to_dict(result: PipelineRunResult) -> dict[str, Any]:
    return {
        "run_path": result.run_path,
        "season": result.season,
        "gameweek": result.gameweek,
        "discovered_video_count": len(result.discovered_videos),
        "input_job_count": len(result.input_jobs),
        "expert_output_count": len(result.expert_outputs),
        "failed_job_count": len(result.failed_jobs),
        "duplicate_source_count": len(result.duplicate_sources),
        "transcript_failure_count": len(result.transcript_failures),
        "synthesis_enabled": result.synthesis_enabled,
        "configured_experts": result.configured_experts,
    }


def get_pipeline_status(run_id: str | None = None) -> dict[str, Any] | None:
    if run_id is not None:
        return PipelineRunRepository().get(run_id)
    return PipelineRunRepository().get_latest()


def _validate_api_input(input_data: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(input_data or {})
    season = payload.get("season")
    if not isinstance(season, str):
        raise ValueError("season is required and must use the YYYY-YY format")
    validate_season(season)
    gameweek = payload.get("gameweek")
    if (
        isinstance(gameweek, bool)
        or not isinstance(gameweek, int)
        or not 1 <= gameweek <= 38
    ):
        raise ValueError("gameweek must be an integer between 1 and 38")
    for field_name in ("per_expert_limit", "archive_limit", "expert_count"):
        value = payload.get(field_name)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 1
        ):
            raise ValueError(f"{field_name} must be a positive integer")
    deadline = payload.get("gameweek_deadline")
    if deadline is not None:
        if not isinstance(deadline, str):
            raise ValueError("gameweek_deadline must be an ISO-8601 timestamp")
        try:
            datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("gameweek_deadline must be an ISO-8601 timestamp") from exc
    return payload


def execute_pipeline_run(
    run_id: str,
    input_data: dict[str, Any],
    *,
    executor: PipelineExecutor = execute_pipeline_sync,
    store: PipelineRunRepository | None = None,
) -> dict[str, Any]:
    """Execute one previously-created run; intended for a background worker."""
    run_store = store or PipelineRunRepository()
    payload = _validate_api_input(input_data)
    run_store.update(run_id, "running")

    try:
        gameweek = int(payload["gameweek"])
        season = str(payload["season"])
        result = executor(
            season=season,
            gameweek=gameweek,
            run_id=run_id,
            per_expert_limit=payload.get("per_expert_limit", 2),
            archive_limit=payload.get("archive_limit", 200),
            gameweek_deadline=payload.get("gameweek_deadline"),
            expert_name=payload.get("expert_name"),
            expert_count=payload.get("expert_count"),
            synthesis_enabled=payload.get("synthesis_enabled", True),
            proxy_settings=load_webshare_proxy_settings(),
            report_service=ReportWriteService(pipeline_run_id=run_id),
            player_catalogue_provider=get_player_catalogue_provider(),
        )
        record = run_store.complete_with_report(
            run_id,
            _pipeline_result_to_dict(result),
        )
    except Exception as exc:
        record = run_store.fail_with_report(run_id, str(exc))
    return record


def _local_dispatch(run_id: str, input_data: dict[str, Any]) -> None:
    Thread(
        target=execute_pipeline_run,
        args=(run_id, input_data),
        daemon=True,
        name=f"pipeline-{run_id}",
    ).start()


_pipeline_dispatcher: PipelineDispatcher = _local_dispatch


def configure_pipeline_dispatcher(dispatcher: PipelineDispatcher | None = None) -> None:
    """Use a remote dispatcher on Modal while retaining local background threads."""
    global _pipeline_dispatcher
    _pipeline_dispatcher = dispatcher or _local_dispatch


def create_pipeline_run(input_data: dict[str, Any] | None) -> dict[str, Any]:
    payload = _validate_api_input(input_data)
    run_id = str(uuid4())
    store = PipelineRunRepository()
    record = store.create_if_idle(run_id, payload)
    try:
        _pipeline_dispatcher(run_id, payload)
    except Exception as exc:
        store.update(
            run_id, "failed", error=f"Could not dispatch pipeline worker: {exc}"
        )
        raise
    # Always acknowledge the accepted state, even if a fast worker has started.
    return record


__all__ = [
    "configure_pipeline_dispatcher",
    "create_pipeline_run",
    "execute_pipeline_run",
    "get_pipeline_status",
]
