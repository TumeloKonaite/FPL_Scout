from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest

from fastapi import Header, HTTPException, status

from src.app.core.config import get_settings


@dataclass(frozen=True)
class AdminPrincipal:
    role: str = "admin"


async def require_admin(authorization: str | None = Header(default=None)) -> AdminPrincipal:
    """Authenticate an administrator without exposing credentials to public clients."""
    settings = get_settings()
    expected_tokens = tuple(
        token for token in (settings.ADMIN_API_TOKEN, settings.PIPELINE_API_TOKEN) if token
    )
    if not expected_tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator authentication is not configured",
        )

    scheme, _, supplied = (authorization or "").partition(" ")
    valid_token = bool(supplied) and any(
        compare_digest(supplied, expected) for expected in expected_tokens
    )
    if scheme.casefold() != "bearer" or not valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AdminPrincipal()
