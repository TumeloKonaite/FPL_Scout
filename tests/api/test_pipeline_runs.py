from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from src.app.api.routes import pipeline_runs
from src.app.core import auth
from src.app.main import create_app


def pending_record() -> dict[str, Any]:
    return {
        "run_id": "run-1",
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": None,
        "updated_at": "2026-01-01T00:00:00+00:00",
        "completed_at": None,
        "duration_seconds": None,
        "current_stage": None,
    }


ADMIN_HEADERS = {"Authorization": "Bearer secret-token"}


def admin_settings() -> SimpleNamespace:
    return SimpleNamespace(ADMIN_API_TOKEN="secret-token", PIPELINE_API_TOKEN="", ENVIRONMENT="production")


def test_create_pipeline_run_returns_202_pending_immediately(monkeypatch) -> None:
    calls: list[dict[str, Any] | None] = []

    def fake_create_pipeline_run(input_data: dict[str, Any] | None) -> dict[str, Any]:
        calls.append(input_data)
        return pending_record()

    monkeypatch.setattr(pipeline_runs, "create_pipeline_run", fake_create_pipeline_run)
    monkeypatch.setattr(auth, "get_settings", admin_settings)
    client = TestClient(create_app())
    response = client.post("/api/pipeline-runs", headers=ADMIN_HEADERS, json={"input_data": {"gameweek": 32}})

    assert response.status_code == 202
    assert response.headers["location"] == "/api/pipeline-runs/run-1"
    assert response.json() == pending_record()
    assert calls == [{"gameweek": 32}]


def test_get_pipeline_run_returns_durable_run(monkeypatch) -> None:
    record = {**pending_record(), "status": "completed", "result": {"report_path": "reports/gw32"}}
    monkeypatch.setattr(
        pipeline_runs,
        "get_pipeline_status",
        lambda run_id: record if run_id == "run-1" else None,
    )
    monkeypatch.setattr(auth, "get_settings", admin_settings)

    response = TestClient(create_app()).get("/api/pipeline-runs/run-1", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == record


def test_get_pipeline_run_returns_404_for_unknown_run_id(monkeypatch) -> None:
    monkeypatch.setattr(pipeline_runs, "get_pipeline_status", lambda run_id: None)
    monkeypatch.setattr(auth, "get_settings", admin_settings)
    response = TestClient(create_app()).get("/api/pipeline-runs/missing", headers=ADMIN_HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Pipeline run not found"}


def test_create_pipeline_run_rejects_invalid_input(monkeypatch) -> None:
    def reject(input_data: dict[str, Any] | None) -> dict[str, Any]:
        raise ValueError("gameweek must be an integer between 1 and 38")

    monkeypatch.setattr(pipeline_runs, "create_pipeline_run", reject)
    monkeypatch.setattr(auth, "get_settings", admin_settings)
    response = TestClient(create_app()).post("/api/pipeline-runs", headers=ADMIN_HEADERS, json={"input_data": {}})
    assert response.status_code == 422
    assert response.json() == {"detail": "gameweek must be an integer between 1 and 38"}


def test_pipeline_start_requires_configured_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        admin_settings,
    )
    monkeypatch.setattr(pipeline_runs, "create_pipeline_run", lambda input_data: pending_record())
    client = TestClient(create_app())

    assert client.post("/api/pipeline-runs", json={"input_data": {"gameweek": 32}}).status_code == 401
    assert client.post(
        "/api/pipeline-runs",
        headers={"Authorization": "Bearer wrong"},
        json={"input_data": {"gameweek": 32}},
    ).status_code == 401
    assert client.post(
        "/api/pipeline-runs",
        headers={"Authorization": "Bearer secret-token"},
        json={"input_data": {"gameweek": 32}},
    ).status_code == 202


def test_production_fails_closed_when_pipeline_token_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(ADMIN_API_TOKEN="", PIPELINE_API_TOKEN="", ENVIRONMENT="production"),
    )
    response = TestClient(create_app()).post(
        "/api/pipeline-runs",
        json={"input_data": {"gameweek": 32}},
    )
    assert response.status_code == 503
