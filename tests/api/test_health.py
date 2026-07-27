from __future__ import annotations

from fastapi.testclient import TestClient

from src.app.core.config import Settings
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
    production = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:secret@pooler.supabase.com:6543/postgres",
        DIRECT_DATABASE_URL="postgresql://user:secret@db.project.supabase.co:5432/postgres",
        DATABASE_POOL_MODE="transaction",
        TRANSCRIPT_STORE="postgres",
        TRANSCRIPT_FILE_FALLBACK_ENABLED=False,
        _env_file=None,
    )
    monkeypatch.setattr(
        "src.app.api.routes.health.get_settings",
        lambda: production,
    )
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
