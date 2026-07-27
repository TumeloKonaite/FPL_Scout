from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.services.video_selection_service import assess_video, extract_gameweeks


VALIDATION_RULE_VERSION = "historical-provenance-v2"
_YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})"
)
_GAMEWEEK_TOKEN_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:gw|game\s*week)\s*#?\s*\d{1,2}(?!\d)",
    re.IGNORECASE,
)
_SEASON_PATTERN = re.compile(
    r"(?<!\d)(\d{2}|\d{4})\s*[/\-]\s*(\d{2}|\d{4})(?!\d)"
)


class ProvenanceValidationError(ValueError):
    def __init__(self, validations: list[dict[str, Any]]) -> None:
        self.validations = validations
        failures = [
            f"{item.get('video_title') or item.get('video_url') or 'unknown source'}: "
            f"{item.get('rejection_reason', 'unverifiable')}"
            for item in validations
            if not item.get("selected")
        ]
        super().__init__(
            "Pre-publication source validation failed: " + "; ".join(failures)
        )


def extract_video_id(video_url: str) -> str:
    if not video_url:
        return ""
    parsed = urlparse(video_url)
    candidate = parse_qs(parsed.query).get("v", [""])[0]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
    match = _YOUTUBE_ID_PATTERN.search(video_url)
    return match.group(1) if match else ""


def extract_seasons(text: str) -> list[str]:
    seasons: list[str] = []
    for first, second in _SEASON_PATTERN.findall(text):
        start = int(first)
        start = start if len(first) == 4 else 2000 + start
        end = int(second)
        expected_end = (start + 1) % 100
        if (len(second) == 2 and end != expected_end) or (
            len(second) == 4 and end != start + 1
        ):
            continue
        season = f"{start:04d}-{expected_end:02d}"
        if season not in seasons:
            seasons.append(season)
    return seasons


def _match_discovered_video(
    job: dict[str, Any], discovered_videos: list[dict[str, Any]]
) -> dict[str, Any]:
    job_url = str(job.get("video_url", ""))
    job_title = str(job.get("video_title", job.get("title", "")))
    job_id = str(job.get("video_id", "")) or extract_video_id(job_url)
    for video in discovered_videos:
        video_url = str(video.get("video_url", ""))
        video_id = str(video.get("video_id", "")) or extract_video_id(video_url)
        if job_id and video_id == job_id:
            return video
        if job_url and video_url == job_url:
            return video
    for video in discovered_videos:
        if job_title and str(video.get("title", "")) == job_title:
            return video
    return {}


def validate_source(
    *,
    gameweek: int,
    season: str,
    gameweek_deadline: str | None,
    source: dict[str, Any],
) -> dict[str, Any]:
    title = str(source.get("video_title", source.get("title", ""))).strip()
    description = str(source.get("description", "")).strip()
    transcript = str(source.get("transcript", "")).strip()
    video_url = str(source.get("video_url", "")).strip()
    video_id = str(source.get("video_id", "")).strip() or extract_video_id(video_url)
    published_at = str(source.get("published_at", "")).strip()
    detected_by_field = {
        "title": extract_gameweeks(title),
        "description": extract_gameweeks(description),
        "transcript": extract_gameweeks(transcript),
    }
    seasons_by_field = {
        "title": extract_seasons(title),
        "description": extract_seasons(description),
    }
    evidence: dict[str, Any] = {
        "video_id": video_id,
        "video_title": title,
        "video_url": video_url,
        "published_at": published_at,
        "requested_gameweek": gameweek,
        "detected_gameweeks_by_field": detected_by_field,
        "detected_seasons_by_field": seasons_by_field,
        "validation_rule_version": VALIDATION_RULE_VERSION,
    }

    for field_name, detected_seasons in seasons_by_field.items():
        if detected_seasons and detected_seasons != [season]:
            return {
                **evidence,
                "selected": False,
                "rejection_reason": f"{field_name}_mentions_different_season",
            }

    for field_name in ("title", "description"):
        detected = detected_by_field[field_name]
        if detected and detected != [gameweek]:
            reason = (
                f"{field_name}_ambiguous_gameweek_mentions"
                if gameweek in detected or len(detected) > 1
                else f"{field_name}_mentions_different_gameweek"
            )
            return {**evidence, "selected": False, "rejection_reason": reason}
    transcript_gameweeks = detected_by_field["transcript"]
    if (
        transcript_gameweeks
        and gameweek not in transcript_gameweeks
        and len(transcript_gameweeks) == 1
    ):
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "transcript_mentions_different_gameweek",
        }

    missing = [
        field_name
        for field_name, value in (
            ("video_id", video_id),
            ("video_url", video_url),
            ("title", title),
            ("transcript", transcript),
        )
        if not value
    ]
    if missing:
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "missing_provenance_evidence",
            "missing_fields": missing,
        }
    if not published_at and season not in seasons_by_field["title"]:
        return {
            **evidence,
            "selected": False,
            "rejection_reason": "missing_season_evidence",
        }

    if not detected_by_field["title"]:
        if not gameweek_deadline:
            return {
                **evidence,
                "selected": False,
                "rejection_reason": "missing_historical_deadline",
            }
        # A generic title is validated by timing and FPL context, not by a
        # gameweek token found later in its description or transcript.
        generic_context = _GAMEWEEK_TOKEN_PATTERN.sub(
            "", " ".join((title, description, transcript))
        )
        assessment = assess_video(
            gameweek=gameweek,
            title=generic_context,
            published_at=published_at,
            season=season,
            gameweek_deadline=gameweek_deadline,
        )
    else:
        assessment = assess_video(
            gameweek=gameweek,
            title=title,
            description=description,
            published_at=published_at,
            season=season,
            gameweek_deadline=gameweek_deadline,
        )
    return {**evidence, **assessment}


def validate_selected_sources(
    *,
    gameweek: int,
    season: str,
    gameweek_deadline: str | None,
    input_jobs: list[dict[str, Any]],
    discovered_videos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []
    for job in input_jobs:
        discovered = _match_discovered_video(job, discovered_videos)
        source = {**discovered, **job}
        source.setdefault("description", discovered.get("description", ""))
        source.setdefault("video_id", discovered.get("video_id", ""))
        validations.append(
            validate_source(
                gameweek=gameweek,
                season=season,
                gameweek_deadline=gameweek_deadline,
                source=source,
            )
        )
    if not validations:
        validations.append(
            {
                "requested_gameweek": gameweek,
                "selected": False,
                "rejection_reason": "no_selected_sources",
                "validation_rule_version": VALIDATION_RULE_VERSION,
            }
        )
    return validations


def require_valid_selected_sources(**kwargs: Any) -> list[dict[str, Any]]:
    validations = validate_selected_sources(**kwargs)
    if any(not item.get("selected") for item in validations):
        raise ProvenanceValidationError(validations)
    return validations


def selected_video_fingerprint(
    validations: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    video_ids = sorted(
        {
            str(item["video_id"])
            for item in validations
            if item.get("selected") and item.get("video_id")
        }
    )
    digest = hashlib.sha256("\n".join(video_ids).encode("utf-8")).hexdigest()
    return digest, video_ids


def fingerprint_overlap(
    first_video_ids: list[str], second_video_ids: list[str]
) -> float:
    first = set(first_video_ids)
    second = set(second_video_ids)
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)
