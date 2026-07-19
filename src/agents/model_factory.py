from __future__ import annotations

import os
from typing import Any

from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from src.app.core.config import get_settings

OPENAI_API_BASE_URL = "https://api.openai.com/v1"


def _get_optional_env(name: str) -> str | None:
    """Return a stripped env var value, treating empty strings as unset."""
    value = os.getenv(name)
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def build_openai_compatible_model(
    model_name: str | None = None,
) -> OpenAIChatCompletionsModel:
    """Build a chat completions model for OpenAI or any compatible provider."""
    settings = get_settings()
    configured_model = model_name or settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY or "unused"
    base_url = _get_optional_env("OPENAI_BASE_URL") or OPENAI_API_BASE_URL

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    return OpenAIChatCompletionsModel(
        model=configured_model,
        openai_client=client,
    )


def build_openai_model(model_name: str | None = None) -> OpenAIChatCompletionsModel:
    """Build a chat completions model pinned to OpenAI's default API endpoint."""
    settings = get_settings()
    configured_model = model_name or settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY or "unused"
    # Pass the official endpoint explicitly. The OpenAI SDK otherwise reads an
    # empty OPENAI_BASE_URL from .env as a malformed URL.
    client = AsyncOpenAI(api_key=api_key, base_url=OPENAI_API_BASE_URL)

    return OpenAIChatCompletionsModel(
        model=configured_model,
        openai_client=client,
    )


async def close_openai_model(model: Any) -> None:
    """Close the AsyncOpenAI client owned by one of our model instances."""
    client = getattr(model, "_client", None)
    close = getattr(client, "close", None)
    if close is not None:
        await close()
