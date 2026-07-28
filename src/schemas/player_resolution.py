from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedPlayerReference(BaseModel):
    name: str = Field(min_length=1)
    playerId: int | None = Field(default=None, gt=0)
    clubHint: str | None = None
    positionHint: Literal["GK", "DEF", "MID", "FWD"] | None = None


ExtractedPlayerInput = str | ExtractedPlayerReference


def normalise_extracted_reference(
    value: ExtractedPlayerInput,
) -> ExtractedPlayerReference:
    if isinstance(value, str):
        return ExtractedPlayerReference(name=value)
    return value


class ResolutionSource(BaseModel):
    expertId: str | None = None
    videoId: str | None = None
    squadRole: Literal[
        "starter", "bench", "current_team", "captain", "vice_captain"
    ]


class FuzzyMatchDiagnostic(BaseModel):
    algorithm: str
    score: float
    runnerUpScore: float | None = None
    margin: float | None = None
    matchedField: str | None = None


class CanonicalPlayerResult(BaseModel):
    playerId: int
    displayName: str
    club: str | None = None
    position: Literal["GK", "DEF", "MID", "FWD"]


class PlayerResolutionEvent(BaseModel):
    rawName: str
    rawPlayerId: int | None = None
    clubHint: str | None = None
    extractedPosition: Literal["GK", "DEF", "MID", "FWD"] | None = None
    source: ResolutionSource
    status: Literal["resolved", "rejected", "duplicate"]
    canonicalPlayerId: int | None = None
    conflictingPlayerId: int | None = None
    canonicalResult: CanonicalPlayerResult | None = None
    method: Literal[
        "player_id",
        "canonical_full_name",
        "canonical_display_name",
        "alias",
        "fuzzy",
    ] | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    match: FuzzyMatchDiagnostic | None = None
    candidatePlayerIds: list[int] = Field(default_factory=list)
    duplicateOfPlayerId: int | None = None


__all__ = [
    "CanonicalPlayerResult",
    "ExtractedPlayerInput",
    "ExtractedPlayerReference",
    "FuzzyMatchDiagnostic",
    "PlayerResolutionEvent",
    "ResolutionSource",
    "normalise_extracted_reference",
]
