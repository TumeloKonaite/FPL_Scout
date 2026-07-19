from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.model_factory import (
    OPENAI_API_BASE_URL,
    build_openai_compatible_model,
    build_openai_model,
    close_openai_model,
)
from src.app.core.config import Settings


DEFAULT_MODEL = "gpt-4.1-mini"


def _settings(**overrides: str) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_build_openai_compatible_model_uses_default_configuration() -> None:
    fake_model = MagicMock(name="model")

    with (
        patch.dict("os.environ", {}, clear=True),
        patch("src.agents.model_factory.get_settings", return_value=_settings()),
        patch("src.agents.model_factory.AsyncOpenAI") as mock_client_class,
        patch(
            "src.agents.model_factory.OpenAIChatCompletionsModel",
            return_value=fake_model,
        ) as mock_model_class,
    ):
        client = mock_client_class.return_value

        result = build_openai_compatible_model()

    assert result is fake_model
    mock_client_class.assert_called_once_with(api_key="unused", base_url=OPENAI_API_BASE_URL)
    mock_model_class.assert_called_once_with(
        model=DEFAULT_MODEL,
        openai_client=client,
    )


def test_build_openai_compatible_model_uses_configured_provider() -> None:
    fake_model = MagicMock(name="model")
    env = {
        "OPENAI_BASE_URL": "https://api.ollama.ai/v1",
    }

    with (
        patch.dict("os.environ", env, clear=True),
        patch(
            "src.agents.model_factory.get_settings",
            return_value=_settings(OPENAI_API_KEY="provider-key", OPENAI_MODEL="llama3.3:70b"),
        ),
        patch("src.agents.model_factory.AsyncOpenAI") as mock_client_class,
        patch(
            "src.agents.model_factory.OpenAIChatCompletionsModel",
            return_value=fake_model,
        ) as mock_model_class,
    ):
        client = mock_client_class.return_value

        result = build_openai_compatible_model()

    assert result is fake_model
    mock_client_class.assert_called_once_with(
        api_key="provider-key",
        base_url="https://api.ollama.ai/v1",
    )
    mock_model_class.assert_called_once_with(
        model="llama3.3:70b",
        openai_client=client,
    )


def test_build_openai_compatible_model_prefers_explicit_model_name() -> None:
    fake_model = MagicMock(name="model")

    with (
        patch.dict("os.environ", {}, clear=True),
        patch(
            "src.agents.model_factory.get_settings",
            return_value=_settings(OPENAI_API_KEY="provider-key", OPENAI_MODEL="ignored-model"),
        ),
        patch("src.agents.model_factory.AsyncOpenAI") as mock_client_class,
        patch(
            "src.agents.model_factory.OpenAIChatCompletionsModel",
            return_value=fake_model,
        ) as mock_model_class,
    ):
        client = mock_client_class.return_value

        result = build_openai_compatible_model("explicit-model")

    assert result is fake_model
    mock_client_class.assert_called_once_with(
        api_key="provider-key", base_url=OPENAI_API_BASE_URL
    )
    mock_model_class.assert_called_once_with(
        model="explicit-model",
        openai_client=client,
    )


def test_build_openai_model_uses_configured_openai_model_without_provider_base_url() -> None:
    fake_model = MagicMock(name="model")
    env = {
        "OPENAI_BASE_URL": "https://ollama.com/v1",
    }

    with (
        patch.dict("os.environ", env, clear=True),
        patch(
            "src.agents.model_factory.get_settings",
            return_value=_settings(OPENAI_API_KEY="openai-key", OPENAI_MODEL="glm-4.7:cloud"),
        ),
        patch("src.agents.model_factory.AsyncOpenAI") as mock_client_class,
        patch(
            "src.agents.model_factory.OpenAIChatCompletionsModel",
            return_value=fake_model,
        ) as mock_model_class,
    ):
        client = mock_client_class.return_value

        result = build_openai_model()

    assert result is fake_model
    mock_client_class.assert_called_once_with(
        api_key="openai-key", base_url=OPENAI_API_BASE_URL
    )
    mock_model_class.assert_called_once_with(
        model="glm-4.7:cloud",
        openai_client=client,
    )


def test_close_openai_model_closes_owned_client() -> None:
    import asyncio

    model = MagicMock()
    model._client.close = AsyncMock()

    asyncio.run(close_openai_model(model))

    model._client.close.assert_awaited_once_with()
