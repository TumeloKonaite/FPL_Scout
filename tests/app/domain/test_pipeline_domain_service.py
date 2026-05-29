from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.app.domain.pipeline.service import PipelineService


def _pipeline_result(run_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        run_path=run_path,
        discovered_videos=[{"video_id": "one"}],
        input_jobs=[object(), object()],
        expert_outputs=[object()],
        failed_jobs=[],
        duplicate_sources=[],
        transcript_failures=[],
        synthesis_enabled=True,
        configured_experts=3,
    )


def test_pipeline_status_before_running() -> None:
    service = PipelineService(executor=lambda **_: _pipeline_result(Path("unused")))

    assert service.get_pipeline_status() == {
        "status": "idle",
        "last_result": None,
        "last_error": None,
    }


def test_successful_pipeline_execution_updates_status(tmp_path) -> None:
    run_path = tmp_path / "runs" / "gw32"

    def executor(**kwargs):
        assert kwargs["gameweek"] == 32
        assert kwargs["output_dir"] == run_path
        assert kwargs["per_expert_limit"] == 2
        return _pipeline_result(run_path)

    service = PipelineService(executor=executor)

    response = service.run_pipeline(gameweek=32, output_dir=run_path)

    assert response == {
        "status": "completed",
        "result": {
            "run_path": run_path,
            "discovered_video_count": 1,
            "input_job_count": 2,
            "expert_output_count": 1,
            "failed_job_count": 0,
            "duplicate_source_count": 0,
            "transcript_failure_count": 0,
            "synthesis_enabled": True,
            "configured_experts": 3,
        },
        "error": None,
    }
    assert service.get_pipeline_status() == {
        "status": "completed",
        "last_result": response["result"],
        "last_error": None,
    }


def test_failed_pipeline_execution_updates_status(tmp_path) -> None:
    def executor(**_):
        raise RuntimeError("pipeline exploded")

    service = PipelineService(executor=executor)

    response = service.run_pipeline(gameweek=32, output_dir=tmp_path / "runs" / "gw32")

    assert response == {
        "status": "failed",
        "result": None,
        "error": "pipeline exploded",
    }
    assert service.get_pipeline_status() == {
        "status": "failed",
        "last_result": None,
        "last_error": "pipeline exploded",
    }
