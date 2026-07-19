from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

from src.adapters.transcript_api import WebshareProxySettings, load_webshare_proxy_settings
from src.app.core.config import get_settings
from src.app.infrastructure.storage.pipeline_run_store import PipelineRunStore
from src.app.infrastructure.storage.runtime_volume import (
    commit_runtime_volume,
    reload_runtime_volume,
)
from src.services.pipeline_service import (
    PipelineRunResult,
    run_pipeline_sync as execute_pipeline_sync,
)

PipelineExecutor = Callable[..., PipelineRunResult]
PipelineDispatcher = Callable[[str, dict[str, Any]], None]
_UNSET = object()


class PipelineService:
    def __init__(self, executor: PipelineExecutor = execute_pipeline_sync) -> None:
        self._executor = executor
        self._status = "idle"
        self._last_result: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._runs: dict[str, dict[str, Any]] = {}

    def run_pipeline(
        self,
        *,
        gameweek: int | None = None,
        output_dir: str | Path | None = None,
        input_data: dict[str, Any] | None | object = _UNSET,
        per_expert_limit: int = 2,
        expert_name: str | None = None,
        expert_count: int | None = None,
        synthesis_enabled: bool = True,
        proxy_settings: WebshareProxySettings | None = None,
    ) -> dict[str, Any]:
        api_run = input_data is not _UNSET
        run_id = str(uuid4()) if api_run else None
        if api_run:
            input_data = input_data or {}
            gameweek = gameweek or input_data.get("gameweek")
            output_dir = output_dir or input_data.get("output_dir")
            per_expert_limit = input_data.get("per_expert_limit", per_expert_limit)
            expert_name = input_data.get("expert_name", expert_name)
            expert_count = input_data.get("expert_count", expert_count)
            synthesis_enabled = input_data.get("synthesis_enabled", synthesis_enabled)

            if output_dir is None and gameweek is not None:
                output_dir = (
                    Path(get_settings().REPORTS_DIR)
                    / f"gw{gameweek}-api-{run_id}"
                )

            self._runs[run_id] = {
                "run_id": run_id,
                "status": "running",
                "result": None,
            }

        self._status = "running"
        self._last_error = None

        try:
            if gameweek is None or output_dir is None:
                raise ValueError("Pipeline run requires gameweek and output_dir")

            pipeline_result = self._executor(
                gameweek=int(gameweek),
                output_dir=output_dir,
                per_expert_limit=per_expert_limit,
                expert_name=expert_name,
                expert_count=expert_count,
                synthesis_enabled=synthesis_enabled,
                proxy_settings=proxy_settings,
            )
        except Exception as exc:
            self._status = "failed"
            self._last_result = None
            self._last_error = str(exc)
            response = {
                "status": self._status,
                "result": None,
                "error": self._last_error,
            }
            if api_run:
                response["run_id"] = run_id
                self._runs[run_id] = {
                    "run_id": run_id,
                    "status": self._status,
                    "result": None,
                    "error": self._last_error,
                }
            return response

        self._status = "completed"
        self._last_result = _pipeline_result_to_dict(pipeline_result)
        response = {
            "status": self._status,
            "result": self._last_result,
            "error": None,
        }
        if api_run:
            response["run_id"] = run_id
            self._runs[run_id] = {
                "run_id": run_id,
                "status": self._status,
                "result": self._last_result,
                "error": None,
            }
        return response

    def get_pipeline_status(self, run_id: str | None = None) -> dict[str, Any] | None:
        if run_id is not None:
            return self._runs.get(run_id)

        return {
            "status": self._status,
            "last_result": self._last_result,
            "last_error": self._last_error,
        }


def _pipeline_result_to_dict(result: PipelineRunResult) -> dict[str, Any]:
    return {
        "run_path": result.run_path,
        "discovered_video_count": len(result.discovered_videos),
        "input_job_count": len(result.input_jobs),
        "expert_output_count": len(result.expert_outputs),
        "failed_job_count": len(result.failed_jobs),
        "duplicate_source_count": len(result.duplicate_sources),
        "transcript_failure_count": len(result.transcript_failures),
        "synthesis_enabled": result.synthesis_enabled,
        "configured_experts": result.configured_experts,
    }


_default_pipeline_service = PipelineService()


def run_pipeline(
    *,
    gameweek: int | None = None,
    output_dir: str | Path | None = None,
    input_data: dict[str, Any] | None | object = _UNSET,
    per_expert_limit: int = 2,
    expert_name: str | None = None,
    expert_count: int | None = None,
    synthesis_enabled: bool = True,
    proxy_settings: WebshareProxySettings | None = None,
) -> dict[str, Any]:
    if input_data is not _UNSET and proxy_settings is None:
        proxy_settings = load_webshare_proxy_settings()

    return _default_pipeline_service.run_pipeline(
        gameweek=gameweek,
        output_dir=output_dir,
        input_data=input_data,
        per_expert_limit=per_expert_limit,
        expert_name=expert_name,
        expert_count=expert_count,
        synthesis_enabled=synthesis_enabled,
        proxy_settings=proxy_settings,
    )


def get_pipeline_status(run_id: str | None = None) -> dict[str, Any] | None:
    if run_id is not None:
        reload_runtime_volume()
        return PipelineRunStore().get(run_id)
    return _default_pipeline_service.get_pipeline_status(run_id)


def _validate_api_input(input_data: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(input_data or {})
    gameweek = payload.get("gameweek")
    if isinstance(gameweek, bool) or not isinstance(gameweek, int) or not 1 <= gameweek <= 38:
        raise ValueError("gameweek must be an integer between 1 and 38")
    for field_name in ("per_expert_limit", "expert_count"):
        value = payload.get(field_name)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 1
        ):
            raise ValueError(f"{field_name} must be a positive integer")
    return payload


def execute_pipeline_run(
    run_id: str,
    input_data: dict[str, Any],
    *,
    executor: PipelineExecutor = execute_pipeline_sync,
    store: PipelineRunStore | None = None,
) -> dict[str, Any]:
    """Execute one previously-created run; intended for a background worker."""
    run_store = store or PipelineRunStore()
    payload = _validate_api_input(input_data)
    reload_runtime_volume()
    run_store.update(run_id, "running")
    commit_runtime_volume()

    try:
        settings = get_settings()
        gameweek = int(payload["gameweek"])
        output_dir = Path(settings.REPORTS_DIR) / f"gw{gameweek}-api-{run_id}"
        result = executor(
            gameweek=gameweek,
            output_dir=output_dir,
            per_expert_limit=payload.get("per_expert_limit", 2),
            expert_name=payload.get("expert_name"),
            expert_count=payload.get("expert_count"),
            synthesis_enabled=payload.get("synthesis_enabled", True),
            proxy_settings=load_webshare_proxy_settings(),
        )
        record = run_store.update(
            run_id,
            "completed",
            result=_pipeline_result_to_dict(result),
        )
    except Exception as exc:
        record = run_store.update(run_id, "failed", error=str(exc))
    commit_runtime_volume()
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
    store = PipelineRunStore()
    record = store.create(run_id, payload)
    commit_runtime_volume()
    try:
        _pipeline_dispatcher(run_id, payload)
    except Exception as exc:
        store.update(run_id, "failed", error=f"Could not dispatch pipeline worker: {exc}")
        commit_runtime_volume()
        raise
    # Always acknowledge the accepted state, even if a fast worker has started.
    return record


__all__ = [
    "PipelineService",
    "configure_pipeline_dispatcher",
    "create_pipeline_run",
    "execute_pipeline_run",
    "get_pipeline_status",
    "run_pipeline",
]
