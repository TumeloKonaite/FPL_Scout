import os

from fastapi.testclient import TestClient

from src.app.main import app, create_app, load_runtime_environment


def test_app_imports_successfully() -> None:
    assert create_app()


def test_load_runtime_environment_populates_process_env(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test-runtime-key\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    load_runtime_environment()

    assert os.environ["OPENAI_API_KEY"] == "test-runtime-key"


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
