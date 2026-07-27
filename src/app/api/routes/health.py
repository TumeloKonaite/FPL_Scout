from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.app.core.config import get_settings
from src.app.infrastructure.database import database_is_ready

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    database_required = (
        settings.ENVIRONMENT.casefold() == "production"
        and settings.TRANSCRIPT_STORE.casefold() == "postgres"
        and bool(settings.DATABASE_URL.strip())
    )
    if database_required and not database_is_ready():
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "database": "unavailable"},
        )
    return {"status": "ok"}
