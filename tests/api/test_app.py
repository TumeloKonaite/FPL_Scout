from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.main import app, create_app


def load_root_app():
    root_main = Path(__file__).resolve().parents[2] / "main.py"
    spec = importlib.util.spec_from_file_location("root_main", root_main)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def test_app_imports_successfully() -> None:
    root_app = load_root_app()

    assert app is root_app
    assert create_app()


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint() -> None:
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello", "session_id": "session-1"})

    assert response.status_code == 200
    assert response.json() == {"response": "hello", "session_id": "session-1"}
