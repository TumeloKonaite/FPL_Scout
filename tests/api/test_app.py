from fastapi.testclient import TestClient

from src.app.main import app, create_app


def test_app_imports_successfully() -> None:
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
