from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.services.report_service import ReportService


class CapturingRepository:
    def __init__(self) -> None:
        self.snapshot: dict[str, Any] | None = None

    def save_snapshot(self, **kwargs: Any) -> None:
        self.snapshot = kwargs


def _contains_null_character(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, Mapping):
        return any(
            _contains_null_character(key) or _contains_null_character(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return any(_contains_null_character(item) for item in value)
    return False


def test_persist_run_removes_null_characters_from_entire_snapshot() -> None:
    repository = CapturingRepository()
    service = ReportService(repository=repository)
    aggregate_report = {
        "season": "2025-26",
        "gameweek": 1,
        "expert_count": 1,
        "player_consensus": [],
        "captaincy_consensus": [],
        "transfer_consensus": [],
        "fixture_insights": [],
        "chip_strategy_consensus": [],
        "disagreements": {},
        "conditional_advice": [],
        "wait_for_news": ["Wait for \x00team news"],
        "expert_team_reveals": [],
    }
    final_report = {
        "season": "2025-26",
        "gameweek": 1,
        "overview": "Overview with \x00invalid data",
        "conclusion": "Conclusion with \x00invalid data",
    }

    service.persist_run(
        run_id="run-1",
        discovered_videos=[
            {"title": "14 VALUE Players for Gameweek 1 \x00"}
        ],
        input_jobs=[{"video_title": "Title \x00"}],
        expert_outputs=[{"video_title": "Title \x00"}],
        aggregate_report=aggregate_report,
        final_report=final_report,
    )

    assert repository.snapshot is not None
    assert not _contains_null_character(repository.snapshot)
    assert repository.snapshot["discovered_videos"][0]["title"] == (
        "14 VALUE Players for Gameweek 1 "
    )
    assert "\x00" not in repository.snapshot["rendered_markdown"]
