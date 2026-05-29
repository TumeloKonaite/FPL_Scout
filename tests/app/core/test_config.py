from __future__ import annotations

from src.app.core.config import Settings, get_settings


def test_settings_loads_values_from_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=test-key",
                "OPENAI_MODEL=test-model",
                "DATA_DIR=custom-data",
                "REPORTS_DIR=custom-reports",
                'CORS_ORIGINS=["http://localhost:5173"]',
                "ENVIRONMENT=test",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.OPENAI_API_KEY == "test-key"
    assert settings.OPENAI_MODEL == "test-model"
    assert settings.DATA_DIR == "custom-data"
    assert settings.REPORTS_DIR == "custom-reports"
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.ENVIRONMENT == "test"


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("OPENAI_MODEL", "cached-model")

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.OPENAI_MODEL == "cached-model"
    get_settings.cache_clear()
