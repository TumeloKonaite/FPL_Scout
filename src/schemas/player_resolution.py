from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExtractedPlayerReference(BaseModel):
    name: str = Field(min_length=1)
    playerId: int | None = Field(default=None, gt=0)
    clubHint: str | None = None
    positionHint: Literal["GK", "DEF", "MID", "FWD"] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


ExtractedPlayerInput = str | ExtractedPlayerReference


def clean_extracted_player_list(value: Any) -> Any:
    """Strip names and discard blank LLM list entries before validation."""
    if not isinstance(value, list):
        return value
    cleaned: list[Any] = []
    for item in value:
        normalized = clean_optional_extracted_player(item)
        if normalized is not None:
            cleaned.append(normalized)
    return cleaned


def clean_optional_extracted_player(value: Any) -> Any:
    """Convert a blank scalar or structured player reference to no evidence."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            stripped = name.strip()
            if not stripped:
                return None
            return {**value, "name": stripped}
    return value


def normalise_extracted_reference(
    value: ExtractedPlayerInput,
) -> ExtractedPlayerReference:
    if isinstance(value, str):
        return ExtractedPlayerReference(name=value.strip())
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
    "clean_extracted_player_list",
    "clean_optional_extracted_player",
    "ExtractedPlayerInput",
    "ExtractedPlayerReference",
    "FuzzyMatchDiagnostic",
    "PlayerResolutionEvent",
    "ResolutionSource",
    "normalise_extracted_reference",
]
