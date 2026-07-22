from __future__ import annotations

from src.adapters.transcript_api import WebshareProxySettings
from src.app.domain.pipeline import service


def test_api_pipeline_loads_webshare_settings(monkeypatch) -> None:
    expected = WebshareProxySettings(
        enabled=True,
        proxy_username="proxy-user",
        proxy_password="proxy-password",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(service, "load_webshare_proxy_settings", lambda: expected)
    monkeypatch.setattr(
        service._default_pipeline_service,
        "run_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed"},
    )

    service.run_pipeline(input_data={"season": "2025-26", "gameweek": 21})

    assert captured["proxy_settings"] == expected


def test_explicit_proxy_settings_are_preserved(monkeypatch) -> None:
    expected = WebshareProxySettings(enabled=False)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        service,
        "load_webshare_proxy_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings should not be reloaded")),
    )
    monkeypatch.setattr(
        service._default_pipeline_service,
        "run_pipeline",
        lambda **kwargs: captured.update(kwargs) or {"status": "completed"},
    )

    service.run_pipeline(input_data={"season": "2025-26", "gameweek": 21}, proxy_settings=expected)

    assert captured["proxy_settings"] == expected
