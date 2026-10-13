from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.app.core import auth


def settings(**overrides: object) -> SimpleNamespace:
    values = {
        "PIPELINE_API_TOKEN": "machine-secret",
        "CLERK_ISSUER": "https://example.clerk.accounts.dev",
        "CLERK_AUTHORIZED_PARTIES": ["http://localhost:3000"],
        "CLERK_ADMIN_USER_IDS": ["user_admin"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def run_immediately(function, *args, **kwargs):
    return function(*args, **kwargs)


def test_pipeline_token_authenticates_machine_client(monkeypatch) -> None:
    monkeypatch.setattr(auth, "get_settings", settings)

    principal = asyncio.run(auth.require_admin(bearer("machine-secret")))

    assert principal.subject == "pipeline-automation"
    assert principal.authentication_method == "pipeline_token"


def test_clerk_admin_token_authenticates_allowed_user(monkeypatch) -> None:
    monkeypatch.setattr(auth, "get_settings", settings)
    monkeypatch.setattr(auth.asyncio, "to_thread", run_immediately)
    monkeypatch.setattr(
        auth,
        "_verify_clerk_token",
        lambda token, *, issuer: {
            "sub": "user_admin",
            "azp": "http://localhost:3000",
        },
    )

    principal = asyncio.run(auth.require_admin(bearer("clerk-session-token")))

    assert principal.subject == "user_admin"
    assert principal.authentication_method == "clerk"


@pytest.mark.parametrize(
    ("claims", "expected_status"),
    [
        ({"sub": "user_other", "azp": "http://localhost:3000"}, 401),
        ({"sub": "user_admin", "azp": "https://evil.example"}, 401),
        ({"sub": "user_admin"}, 401),
    ],
)
def test_clerk_token_requires_admin_subject_and_authorized_party(
    monkeypatch, claims: dict[str, str], expected_status: int
) -> None:
    monkeypatch.setattr(auth, "get_settings", settings)
    monkeypatch.setattr(auth.asyncio, "to_thread", run_immediately)
    monkeypatch.setattr(
        auth, "_verify_clerk_token", lambda token, *, issuer: claims
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.require_admin(bearer("clerk-session-token")))

    assert error.value.status_code == expected_status


def test_authentication_fails_closed_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: settings(
            PIPELINE_API_TOKEN="",
            CLERK_ISSUER="",
            CLERK_AUTHORIZED_PARTIES=[],
            CLERK_ADMIN_USER_IDS=[],
        ),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.require_admin(None))

    assert error.value.status_code == 503
