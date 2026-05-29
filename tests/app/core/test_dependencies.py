from __future__ import annotations

from src.app.core.config import Settings
from src.app.core.dependencies import get_app_settings


def test_get_app_settings_returns_settings() -> None:
    get_app_settings.cache_clear()

    settings = get_app_settings()

    assert isinstance(settings, Settings)
    assert hasattr(settings, "OPENAI_MODEL")
    get_app_settings.cache_clear()


def test_get_app_settings_returns_cached_instance() -> None:
    get_app_settings.cache_clear()

    first = get_app_settings()
    second = get_app_settings()

    assert first is second
    get_app_settings.cache_clear()
