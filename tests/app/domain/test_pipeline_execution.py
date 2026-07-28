from __future__ import annotations

from types import SimpleNamespace

from src.app.domain.pipeline.service import execute_pipeline_run


class _Store:
    def update(self, run_id: str, status: str) -> None:
        assert (run_id, status) == ("run-1", "running")

    def complete_with_report(self, run_id: str, result: dict) -> dict:
        return {"run_id": run_id, "status": "completed", "result": result}

    def fail_with_report(self, run_id: str, error: str) -> dict:
        raise AssertionError(error)


def test_worker_injects_season_aware_catalogue_provider() -> None:
    captured = {}

    def executor(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            run_path="run-1",
            season="2025-26",
            gameweek=31,
            discovered_videos=[],
            input_jobs=[],
            expert_outputs=[],
            failed_jobs=[],
            duplicate_sources=[],
            transcript_failures=[],
            synthesis_enabled=True,
            configured_experts=0,
        )

    result = execute_pipeline_run(
        "run-1",
        {"season": "2025-26", "gameweek": 31},
        executor=executor,
        store=_Store(),  # type: ignore[arg-type]
    )

    provider = captured["player_catalogue_provider"]
    assert callable(provider.get_catalogue)
    assert result["status"] == "completed"
