from __future__ import annotations

from fastapi.testclient import TestClient

from src.app.main import create_app


def test_health_returns_200(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.app.api.routes.health.database_is_ready",
        lambda: True,
    )
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_production_database_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.app.api.routes.health.database_is_ready",
        lambda: False,
    )
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"status": "unavailable", "database": "unavailable"}
    }
