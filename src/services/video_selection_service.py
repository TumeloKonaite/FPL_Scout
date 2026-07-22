from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from src.schemas.report_identity import parse_season_start_year


_GAMEWEEK_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:gw|game\s*week)\s*#?\s*(\d{1,2})(?!\d)",
    re.IGNORECASE,
)

_FPL_CONTEXT_KEYWORDS = (
    "fpl",
    "fantasy premier league",
    "preview",
    "deadline",
    "team selection",
    "watchlist",
    "wildcard",
    "captain",
    "captaincy",
    "transfer",
    "draft",
    "best picks",
)

_IRRELEVANT_KEYWORDS = (
    "stream highlights",
    "career mode",
    "fc 26",
    "eafc",
    "reaction",
    "vlog",
)

_END_OF_SEASON_KEYWORDS = (
    "end of season",
    "end-of-season",
    "season review",
    "season recap",
    "season summary",
    "final rank",
    "overall rank reveal",
)

DEFAULT_WINDOW_DAYS_BEFORE = 10
DEFAULT_WINDOW_DAYS_AFTER = 2


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def extract_gameweeks(text: str) -> list[int]:
    """Return explicit FPL gameweek references in first-seen order."""
    found: list[int] = []
    for match in _GAMEWEEK_PATTERN.finditer(text):
        gameweek = int(match.group(1))
        if 1 <= gameweek <= 38 and gameweek not in found:
            found.append(gameweek)
    return found


def _has_fpl_context(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in _FPL_CONTEXT_KEYWORDS)


def _looks_irrelevant(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in _IRRELEVANT_KEYWORDS)


def _is_end_of_season_content(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in _END_OF_SEASON_KEYWORDS)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _season_contains(timestamp: datetime, season: str | None) -> bool:
    if season is None:
        return True
    start_year = parse_season_start_year(season)
    start = datetime(start_year, 7, 1, tzinfo=UTC)
    end = datetime(start_year + 1, 7, 1, tzinfo=UTC)
    return start <= timestamp < end


def _publication_window(
    deadline: str | None,
    *,
    days_before: int,
    days_after: int,
) -> tuple[datetime, datetime] | None:
    parsed = _parse_timestamp(deadline)
    if parsed is None:
        return None
    return parsed - timedelta(days=days_before), parsed + timedelta(days=days_after)


def assess_video(
    *,
    gameweek: int,
    title: str,
    description: str = "",
    transcript: str = "",
    published_at: str | None = None,
    season: str | None = None,
    gameweek_deadline: str | None = None,
    window_days_before: int = DEFAULT_WINDOW_DAYS_BEFORE,
    window_days_after: int = DEFAULT_WINDOW_DAYS_AFTER,
) -> dict[str, Any]:
    """Assess a candidate and return persistable selection evidence."""
    combined_text = " ".join(
        part for part in (title, description, transcript) if part
    ).strip()
    detected = extract_gameweeks(combined_text)
    evidence: dict[str, Any] = {
        "requested_gameweek": gameweek,
        "detected_gameweeks": detected,
        "published_at": published_at or "",
    }

    if not combined_text:
        return {**evidence, "selected": False, "rejection_reason": "missing_content"}
    if _is_end_of_season_content(combined_text):
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "end_of_season_content",
        }
    if _looks_irrelevant(combined_text):
        return {**evidence, "selected": False, "rejection_reason": "irrelevant_content"}
    if detected and detected != [gameweek]:
        reason = (
            "ambiguous_gameweek_mentions"
            if gameweek in detected or len(detected) > 1
            else "mentions_different_gameweek"
        )
        return {**evidence, "selected": False, "rejection_reason": reason}

    published = _parse_timestamp(published_at)
    window = _publication_window(
        gameweek_deadline,
        days_before=window_days_before,
        days_after=window_days_after,
    )

    if detected == [gameweek]:
        if published is not None and not _season_contains(published, season):
            return {
                **evidence,
                "selected": False,
                "rejection_reason": "outside_requested_season",
            }
        if published is not None and window is not None and not (
            window[0] <= published <= window[1]
        ):
            return {
                **evidence,
                "selected": False,
                "rejection_reason": "outside_gameweek_window",
            }
        return {**evidence, "selected": True, "selection_reason": "exact_gameweek_match"}

    if published is None:
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "missing_publication_date",
        }
    if window is None:
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "missing_gameweek_evidence",
        }
    if not (window[0] <= published <= window[1]):
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "outside_gameweek_window",
        }
    if not _has_fpl_context(combined_text):
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "missing_fpl_context",
        }
    return {**evidence, "selected": True, "selection_reason": "publication_date_match"}


def is_relevant_video(
    *,
    gameweek: int,
    title: str,
    transcript: str = "",
    description: str = "",
    published_at: str | None = None,
    season: str | None = None,
    gameweek_deadline: str | None = None,
) -> bool:
    return bool(
        assess_video(
            gameweek=gameweek,
            title=title,
            description=description,
            transcript=transcript,
            published_at=published_at,
            season=season,
            gameweek_deadline=gameweek_deadline,
        )["selected"]
    )


def filter_relevant_videos(
    candidates: Sequence[dict[str, Any]],
    *,
    gameweek: int,
    season: str | None = None,
    gameweek_deadline: str | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        evidence = assess_video(
            gameweek=gameweek,
            title=str(candidate.get("title", "")),
            description=str(candidate.get("description", "")),
            transcript=str(candidate.get("transcript", "")),
            published_at=str(candidate.get("published_at", "")),
            season=season,
            gameweek_deadline=gameweek_deadline,
        )
        candidate.update(evidence)
        if evidence["selected"]:
            selected.append(candidate)
    return selected
