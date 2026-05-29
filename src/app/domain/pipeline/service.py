from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.adapters.transcript_api import WebshareProxySettings
from src.app.core.config import get_settings
from src.services.pipeline_service import (
    PipelineRunResult,
    run_pipeline_sync as execute_pipeline_sync,
)

PipelineExecutor = Callable[..., PipelineRunResult]
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
    return _default_pipeline_service.get_pipeline_status(run_id)


__all__ = [
    "PipelineService",
    "get_pipeline_status",
    "run_pipeline",
]
