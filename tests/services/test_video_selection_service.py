from __future__ import annotations

from src.services.video_selection_service import assess_video, filter_relevant_videos, is_relevant_video


def test_is_relevant_video_accepts_matching_gameweek_reference() -> None:
    assert is_relevant_video(
        gameweek=32,
        title="FPL GW32 Deadline Stream",
        transcript="",
    )


def test_is_relevant_video_rejects_generic_fpl_context_without_date_evidence() -> None:
    assert not is_relevant_video(
        gameweek=32,
        title="My latest thoughts",
        transcript="This FPL preview covers captaincy and transfer plans for the week.",
    )


def test_is_relevant_video_rejects_irrelevant_upload() -> None:
    assert not is_relevant_video(
        gameweek=32,
        title="EAFC 26 Career Mode Reaction",
        transcript="A fun stream highlights package.",
    )


def test_filter_relevant_videos_keeps_only_relevant_candidates() -> None:
    selected = filter_relevant_videos(
        [
            {"video_id": "keep-1", "title": "GW32 Best Picks", "transcript": ""},
            {"video_id": "drop-1", "title": "Weekend vlog", "transcript": ""},
            {"video_id": "keep-2", "title": "Q&A", "transcript": "FPL wildcard draft and captaincy preview."},
        ],
        gameweek=32,
    )

    assert [item["video_id"] for item in selected] == ["keep-1"]


def test_conflicting_and_ambiguous_gameweek_mentions_are_rejected() -> None:
    conflicting = assess_video(gameweek=31, title="FPL GW38 final team")
    ambiguous = assess_video(gameweek=31, title="GW31 review and GW32 preview")

    assert conflicting["rejection_reason"] == "mentions_different_gameweek"
    assert conflicting["detected_gameweeks"] == [38]
    assert ambiguous["rejection_reason"] == "ambiguous_gameweek_mentions"


def test_date_window_can_support_candidate_without_gameweek_mention() -> None:
    evidence = assess_video(
        gameweek=31,
        title="FPL team selection and captaincy",
        published_at="2026-03-27T18:00:00Z",
        season="2025-26",
        gameweek_deadline="2026-03-28T11:00:00Z",
    )

    assert evidence["selected"] is True
    assert evidence["selection_reason"] == "publication_date_match"


def test_missing_date_requires_exact_gameweek_evidence() -> None:
    assert assess_video(gameweek=31, title="FPL captain picks")["rejection_reason"] == (
        "missing_publication_date"
    )
    assert assess_video(gameweek=31, title="FPL GW31 captain picks")["selection_reason"] == (
        "exact_gameweek_match"
    )


def test_end_of_season_review_is_rejected() -> None:
    evidence = assess_video(gameweek=31, title="FPL GW31 end of season review")
    assert evidence["rejection_reason"] == "end_of_season_content"


def test_exact_match_outside_deadline_window_is_rejected() -> None:
    evidence = assess_video(
        gameweek=31,
        title="FPL GW31 retrospective",
        published_at="2026-05-20T18:00:00Z",
        season="2025-26",
        gameweek_deadline="2026-03-28T11:00:00Z",
    )
    assert evidence["rejection_reason"] == "outside_gameweek_window"
