from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.app.domain.pipeline.service import PipelineService


def _pipeline_result(run_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        run_path=run_path,
        season="2025-26",
        gameweek=32,
        discovered_videos=[{"video_id": "one"}],
        input_jobs=[object(), object()],
        expert_outputs=[object()],
        failed_jobs=[],
        duplicate_sources=[{"source": "duplicate"}],
        transcript_failures=[],
        synthesis_enabled=False,
        configured_experts=2,
    )


def test_pipeline_service_executes_with_explicit_arguments(tmp_path) -> None:
    calls: list[dict[str, Any]] = []
    run_path = tmp_path / "runs" / "gw32"

    def executor(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return _pipeline_result(run_path)

    service = PipelineService(executor=executor)

    response = service.run_pipeline(
        season="2025-26",
        gameweek=32,
        output_dir=run_path,
        per_expert_limit=1,
        synthesis_enabled=False,
    )

    assert response["status"] == "completed"
    assert response["error"] is None
    assert response["result"] == {
        "run_path": run_path,
        "season": "2025-26",
        "gameweek": 32,
        "discovered_video_count": 1,
        "input_job_count": 2,
        "expert_output_count": 1,
        "failed_job_count": 0,
        "duplicate_source_count": 1,
        "transcript_failure_count": 0,
        "synthesis_enabled": False,
        "configured_experts": 2,
    }
    assert calls[0]["gameweek"] == 32
    assert calls[0]["output_dir"] == run_path
    assert calls[0]["per_expert_limit"] == 1


def test_pipeline_service_tracks_api_run_by_generated_run_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("src.app.domain.pipeline.service.uuid4", lambda: "run-123")
    run_path = tmp_path / "runs" / "gw33"
    service = PipelineService(executor=lambda **_: _pipeline_result(run_path))

    response = service.run_pipeline(
        input_data={
            "season": "2025-26",
            "gameweek": 33,
            "output_dir": run_path,
            "synthesis_enabled": False,
        }
    )

    assert response["run_id"] == "run-123"
    assert response["status"] == "completed"
    assert service.get_pipeline_status("run-123") == {
        "run_id": "run-123",
        "status": "completed",
        "result": response["result"],
        "error": None,
    }


def test_pipeline_service_returns_failed_status_when_required_inputs_are_missing() -> None:
    service = PipelineService(executor=lambda **_: _pipeline_result(Path("unused")))

    response = service.run_pipeline(gameweek=32)

    assert response == {
        "status": "failed",
        "result": None,
        "error": "Pipeline run requires season, gameweek and output_dir",
    }
    assert service.get_pipeline_status()["last_error"] == (
        "Pipeline run requires season, gameweek and output_dir"
    )
