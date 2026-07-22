from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.app.domain.pipeline import service as pipeline_service
from src.app.domain.pipeline.service import execute_pipeline_run
from src.app.infrastructure.storage.pipeline_run_store import PipelineRunStore


def fake_result() -> SimpleNamespace:
    return SimpleNamespace(
        run_path=Path("reports/gw32"),
        season="2025-26",
        gameweek=32,
        discovered_videos=[],
        input_jobs=[],
        expert_outputs=[],
        failed_jobs=[],
        duplicate_sources=[],
        transcript_failures=[],
        synthesis_enabled=True,
        configured_experts=0,
    )


def test_worker_transitions_running_then_completed(tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    store.create("run-1", {"season": "2025-26", "gameweek": 32})
    observed: list[str] = []

    def executor(**kwargs):
        observed.append(store.get("run-1")["status"])
        return fake_result()

    result = execute_pipeline_run("run-1", {"season": "2025-26", "gameweek": 32}, executor=executor, store=store)

    assert observed == ["running"]
    assert result["status"] == "completed"


def test_worker_exception_transitions_to_failed(tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    store.create("run-1", {"season": "2025-26", "gameweek": 32})

    def executor(**kwargs):
        raise RuntimeError("provider unavailable")

    result = execute_pipeline_run("run-1", {"season": "2025-26", "gameweek": 32}, executor=executor, store=store)

    assert result["status"] == "failed"
    assert result["error"] == "provider unavailable"


def test_worker_passes_webshare_settings_to_pipeline(monkeypatch, tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    store.create("run-1", {"season": "2025-26", "gameweek": 32})
    proxy_settings = object()
    monkeypatch.setattr(
        pipeline_service,
        "load_webshare_proxy_settings",
        lambda: proxy_settings,
    )

    def executor(**kwargs):
        assert kwargs["proxy_settings"] is proxy_settings
        return fake_result()

    result = execute_pipeline_run("run-1", {"season": "2025-26", "gameweek": 32}, executor=executor, store=store)
    assert result["status"] == "completed"
