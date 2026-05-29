from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.adapters.transcript_api import WebshareProxySettings
from src.services.pipeline_service import (
    PipelineRunResult,
    run_pipeline_sync as execute_pipeline_sync,
)

PipelineExecutor = Callable[..., PipelineRunResult]


class PipelineService:
    def __init__(self, executor: PipelineExecutor = execute_pipeline_sync) -> None:
        self._executor = executor
        self._status = "idle"
        self._last_result: dict[str, Any] | None = None
        self._last_error: str | None = None

    def run_pipeline(
        self,
        *,
        gameweek: int,
        output_dir: str | Path,
        per_expert_limit: int = 2,
        expert_name: str | None = None,
        expert_count: int | None = None,
        synthesis_enabled: bool = True,
        proxy_settings: WebshareProxySettings | None = None,
    ) -> dict[str, Any]:
        self._status = "running"
        self._last_error = None

        try:
            pipeline_result = self._executor(
                gameweek=gameweek,
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
            return {
                "status": self._status,
                "result": None,
                "error": self._last_error,
            }

        self._status = "completed"
        self._last_result = _pipeline_result_to_dict(pipeline_result)
        return {
            "status": self._status,
            "result": self._last_result,
            "error": None,
        }

    def get_pipeline_status(self) -> dict[str, Any]:
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
    gameweek: int,
    output_dir: str | Path,
    per_expert_limit: int = 2,
    expert_name: str | None = None,
    expert_count: int | None = None,
    synthesis_enabled: bool = True,
    proxy_settings: WebshareProxySettings | None = None,
) -> dict[str, Any]:
    return _default_pipeline_service.run_pipeline(
        gameweek=gameweek,
        output_dir=output_dir,
        per_expert_limit=per_expert_limit,
        expert_name=expert_name,
        expert_count=expert_count,
        synthesis_enabled=synthesis_enabled,
        proxy_settings=proxy_settings,
    )


def get_pipeline_status() -> dict[str, Any]:
    return _default_pipeline_service.get_pipeline_status()


__all__ = [
    "PipelineService",
    "get_pipeline_status",
    "run_pipeline",
]
