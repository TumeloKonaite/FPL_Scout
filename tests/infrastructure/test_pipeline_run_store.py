from __future__ import annotations

import pytest

from src.app.infrastructure.storage.pipeline_run_store import ActivePipelineRunError, PipelineRunStore


def test_run_status_survives_store_instances(tmp_path) -> None:
    first_instance = PipelineRunStore(tmp_path / "runs")
    first_instance.create("run-1", {"gameweek": 32})
    first_instance.update("run-1", "running")

    assert PipelineRunStore(tmp_path / "runs").get("run-1")["status"] == "running"


def test_terminal_status_is_persisted(tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    store.create("run-1", {"gameweek": 32})
    completed = store.update("run-1", "completed", result={"run_path": "reports/gw32"})

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert store.get("run-1")["result"] == {"run_path": "reports/gw32"}


def test_duplicate_active_runs_are_rejected(tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    first = store.create_if_idle("run-1", {"gameweek": 32})

    assert first["status"] == "queued"
    with pytest.raises(ActivePipelineRunError, match="run-1"):
        store.create_if_idle("run-2", {"gameweek": 32})


def test_terminal_run_allows_next_run(tmp_path) -> None:
    store = PipelineRunStore(tmp_path / "runs")
    store.create_if_idle("run-1", {"gameweek": 32})
    store.update("run-1", "failed", error="provider unavailable")

    assert store.create_if_idle("run-2", {"gameweek": 32})["status"] == "queued"
