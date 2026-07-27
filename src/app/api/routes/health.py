from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.app.infrastructure.database import database_is_ready

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    if not database_is_ready():
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "database": "unavailable"},
        )
    return {"status": "ok"}
