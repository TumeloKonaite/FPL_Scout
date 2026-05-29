from __future__ import annotations

from fastapi.testclient import TestClient

from src.app.core.config import Settings
from src.app.core.dependencies import get_app_settings
from src.app.main import create_app


def test_chat_endpoint_uses_settings_dependency() -> None:
    app = create_app()
    calls = 0

    def override_settings() -> Settings:
        nonlocal calls
        calls += 1
        return Settings(_env_file=None, OPENAI_MODEL="test-model")

    app.dependency_overrides[get_app_settings] = override_settings
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello", "session_id": "session-1"})

    assert response.status_code == 200
    assert response.json() == {"response": "hello", "session_id": "session-1"}
    assert calls == 1
