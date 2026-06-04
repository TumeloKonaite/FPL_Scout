from __future__ import annotations

from src.app.core.config import Settings, bootstrap_data_directories, get_settings


def test_settings_loads_values_from_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    monkeypatch.delenv("REPORTS_DIR", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

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
    assert settings.RAW_DATA_DIR == "custom-data/raw"
    assert settings.PROCESSED_DATA_DIR == "custom-data/processed"
    assert settings.TRANSCRIPTS_DIR == "custom-data/transcripts"
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.ENVIRONMENT == "test"


def test_data_subdirectories_derive_from_data_dir(tmp_path) -> None:
    settings = Settings(DATA_DIR=str(tmp_path / "runtime"), _env_file=None)

    assert settings.REPORTS_DIR == str(tmp_path / "runtime" / "reports")
    assert settings.RAW_DATA_DIR == str(tmp_path / "runtime" / "raw")
    assert settings.PROCESSED_DATA_DIR == str(tmp_path / "runtime" / "processed")
    assert settings.TRANSCRIPTS_DIR == str(tmp_path / "runtime" / "transcripts")


def test_bootstrap_data_directories_creates_runtime_directories(tmp_path) -> None:
    settings = Settings(DATA_DIR=str(tmp_path / "runtime"), _env_file=None)

    bootstrap_data_directories(settings)

    assert (tmp_path / "runtime" / "reports").is_dir()
    assert (tmp_path / "runtime" / "raw").is_dir()
    assert (tmp_path / "runtime" / "processed").is_dir()
    assert (tmp_path / "runtime" / "transcripts").is_dir()


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("OPENAI_MODEL", "cached-model")

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.OPENAI_MODEL == "cached-model"
    get_settings.cache_clear()
