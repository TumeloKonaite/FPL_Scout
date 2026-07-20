from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LatestRecommendationsResponse(BaseModel):
    gameweek: int | None = None
    last_updated_at: str | None = None
    available: bool = True
    report: dict[str, Any]


class CurrentGameweekResponse(BaseModel):
    gameweek: int | None = None
    deadline: str | None = None
    last_updated_at: str | None = None
    recommendations_available: bool
