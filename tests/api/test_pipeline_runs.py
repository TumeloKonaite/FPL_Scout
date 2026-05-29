from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from src.app.api.routes import pipeline_runs
from src.app.main import create_app


def test_create_pipeline_run_returns_run_id_and_status(monkeypatch) -> None:
    calls: list[dict[str, Any] | None] = []

    def fake_run_pipeline(*, input_data: dict[str, Any] | None) -> dict[str, Any]:
        calls.append(input_data)
        return {
            "run_id": "run-1",
            "status": "completed",
            "result": {"gameweek": 32},
        }

    monkeypatch.setattr(pipeline_runs, "run_pipeline", fake_run_pipeline)
    client = TestClient(create_app())

    response = client.post(
        "/api/pipeline-runs",
        json={"input_data": {"gameweek": 32}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run-1",
        "status": "completed",
        "result": {"gameweek": 32},
    }
    assert calls == [{"gameweek": 32}]


def test_get_pipeline_run_returns_saved_run(monkeypatch) -> None:
    saved_runs = {
        "run-1": {
            "run_id": "run-1",
            "status": "completed",
            "result": {"report_path": "reports/gw32"},
        }
    }

    def fake_get_pipeline_status(run_id: str) -> dict[str, Any] | None:
        return saved_runs.get(run_id)

    monkeypatch.setattr(pipeline_runs, "get_pipeline_status", fake_get_pipeline_status)
    client = TestClient(create_app())

    response = client.get("/api/pipeline-runs/run-1")

    assert response.status_code == 200
    assert response.json() == saved_runs["run-1"]


def test_get_pipeline_run_returns_404_for_unknown_run_id(monkeypatch) -> None:
    def fake_get_pipeline_status(run_id: str) -> None:
        return None

    monkeypatch.setattr(pipeline_runs, "get_pipeline_status", fake_get_pipeline_status)
    client = TestClient(create_app())

    response = client.get("/api/pipeline-runs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Pipeline run not found"}


def test_create_pipeline_run_delegates_to_domain_service(monkeypatch) -> None:
    called = False

    def fake_run_pipeline(*, input_data: dict[str, Any] | None) -> dict[str, Any]:
        nonlocal called
        called = True
        assert input_data == {"gameweek": 33, "per_expert_limit": 1}
        return {
            "run_id": "domain-generated-id",
            "status": "completed",
            "result": None,
        }

    monkeypatch.setattr(pipeline_runs, "run_pipeline", fake_run_pipeline)
    client = TestClient(create_app())

    response = client.post(
        "/api/pipeline-runs",
        json={"input_data": {"gameweek": 33, "per_expert_limit": 1}},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == "domain-generated-id"
    assert called is True
