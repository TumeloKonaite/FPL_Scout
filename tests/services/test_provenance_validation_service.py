from __future__ import annotations

import pytest

from src.services.provenance_validation_service import (
    ProvenanceValidationError,
    require_valid_selected_sources,
    selected_video_fingerprint,
    validate_source,
)


BASE_SOURCE = {
    "video_id": "abcdefghijk",
    "video_url": "https://www.youtube.com/watch?v=abcdefghijk",
    "video_title": "FPL GW31 team selection",
    "published_at": "2026-03-19T18:00:00Z",
    "transcript": "My captain and transfers are discussed here.",
}


def test_title_mismatch_blocks_publication() -> None:
    evidence = validate_source(
        gameweek=31,
        season="2025-26",
        gameweek_deadline="2026-03-20T18:30:00Z",
        source={**BASE_SOURCE, "video_title": "FPL GW38 team selection"},
    )

    assert evidence["selected"] is False
    assert evidence["rejection_reason"] == "title_mentions_different_gameweek"


@pytest.mark.parametrize("field_name", ["description", "transcript"])
def test_non_title_mismatch_blocks_publication(field_name: str) -> None:
    evidence = validate_source(
        gameweek=31,
        season="2025-26",
        gameweek_deadline="2026-03-20T18:30:00Z",
        source={**BASE_SOURCE, field_name: "This is my GW36 team selection."},
    )

    assert evidence["selected"] is False
    assert evidence["rejection_reason"] == (
        f"{field_name}_mentions_different_gameweek"
    )


def test_generic_historical_title_requires_deadline_and_valid_timing() -> None:
    generic = {
        **BASE_SOURCE,
        "video_title": "My latest FPL team selection",
    }

    missing_deadline = validate_source(
        gameweek=31,
        season="2025-26",
        gameweek_deadline=None,
        source=generic,
    )
    valid = validate_source(
        gameweek=31,
        season="2025-26",
        gameweek_deadline="2026-03-20T18:30:00Z",
        source=generic,
    )

    assert missing_deadline["rejection_reason"] == "missing_historical_deadline"
    assert valid["selected"] is True
    assert valid["selection_reason"] == "publication_date_match"


def test_missing_provenance_fails_closed() -> None:
    with pytest.raises(ProvenanceValidationError, match="missing_provenance"):
        require_valid_selected_sources(
            gameweek=31,
            season="2025-26",
            gameweek_deadline="2026-03-20T18:30:00Z",
            input_jobs=[{**BASE_SOURCE, "video_url": "", "video_id": ""}],
            discovered_videos=[],
        )


def test_fingerprint_is_stable_for_video_id_set() -> None:
    first = [
        {"selected": True, "video_id": "two"},
        {"selected": True, "video_id": "one"},
    ]
    second = [
        {"selected": True, "video_id": "one"},
        {"selected": True, "video_id": "two"},
        {"selected": True, "video_id": "one"},
    ]

    assert selected_video_fingerprint(first) == selected_video_fingerprint(second)


def test_same_gameweek_from_another_season_is_rejected() -> None:
    evidence = validate_source(
        gameweek=30,
        season="2025-26",
        gameweek_deadline="2026-03-14T13:30:00Z",
        source={
            **BASE_SOURCE,
            "video_title": "FPL GW30 team selection 2024/25",
        },
    )

    assert evidence["rejection_reason"] == "title_mentions_different_season"


def test_transcript_can_discuss_multiple_gameweeks_when_title_is_explicit() -> None:
    evidence = validate_source(
        gameweek=31,
        season="2025-26",
        gameweek_deadline="2026-03-20T18:30:00Z",
        source={
            **BASE_SOURCE,
            "video_title": "FPL GW31 team selection 2025/26",
            "transcript": "GW30 was poor; GW31 is next and GW32 planning matters.",
        },
    )

    assert evidence["selected"] is True
