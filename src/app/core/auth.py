from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from hmac import compare_digest
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from src.app.core.config import get_settings


@dataclass(frozen=True)
class AdminPrincipal:
    subject: str = "admin"
    authentication_method: str = "dependency_override"
    role: str = "admin"


admin_bearer = HTTPBearer(
    auto_error=False,
    description="Clerk administrator JWT or machine-only pipeline bearer token.",
)


@lru_cache(maxsize=8)
def _clerk_jwks_client(issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{issuer.rstrip('/')}/.well-known/jwks.json")


def _verify_clerk_token(token: str, *, issuer: str) -> dict[str, Any]:
    normalized_issuer = issuer.rstrip("/")
    signing_key = _clerk_jwks_client(normalized_issuer).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=normalized_issuer,
        options={
            "require": ["exp", "iat", "iss", "sub"],
            "verify_aud": False,
        },
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Administrator authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(admin_bearer),
    ],
) -> AdminPrincipal:
    """Authorize a Clerk administrator or a trusted pipeline automation client."""
    settings = get_settings()
    clerk_configured = bool(
        settings.CLERK_ISSUER
        and settings.CLERK_AUTHORIZED_PARTIES
        and settings.CLERK_ADMIN_USER_IDS
    )
    if not settings.PIPELINE_API_TOKEN and not clerk_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator authentication is not configured",
        )

    scheme = credentials.scheme if credentials is not None else ""
    supplied = credentials.credentials if credentials is not None else ""
    if scheme.casefold() != "bearer" or not supplied:
        raise _unauthorized()

    if settings.PIPELINE_API_TOKEN and compare_digest(
        supplied, settings.PIPELINE_API_TOKEN
    ):
        return AdminPrincipal(
            subject="pipeline-automation", authentication_method="pipeline_token"
        )

    if not clerk_configured:
        raise _unauthorized()

    try:
        claims = await asyncio.to_thread(
            _verify_clerk_token, supplied, issuer=settings.CLERK_ISSUER
        )
    except (PyJWTError, ValueError, OSError):
        raise _unauthorized() from None

    subject = claims.get("sub")
    authorized_party = claims.get("azp")
    if (
        not isinstance(subject, str)
        or subject not in settings.CLERK_ADMIN_USER_IDS
        or not isinstance(authorized_party, str)
        or authorized_party not in settings.CLERK_AUTHORIZED_PARTIES
    ):
        raise _unauthorized()

    return AdminPrincipal(subject=subject, authentication_method="clerk")
