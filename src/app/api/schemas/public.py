from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PublicRecommendationResponse(BaseModel):
    season: str
    gameweek: int | None = None
    last_updated_at: datetime | None = None
    available: bool = True
    report: dict[str, Any]


class GameweekReportSummary(BaseModel):
    gameweek: int
    last_updated_at: datetime
    has_suggested_team: bool


class SeasonGameweekIndex(BaseModel):
    season: str
    gameweeks: list[GameweekReportSummary]


class AvailableGameweeksResponse(BaseModel):
    seasons: list[SeasonGameweekIndex]


LatestRecommendationsResponse = PublicRecommendationResponse


class CurrentGameweekResponse(BaseModel):
    gameweek: int | None = None
    deadline: str | None = None
    last_updated_at: str | None = None
    recommendations_available: bool
