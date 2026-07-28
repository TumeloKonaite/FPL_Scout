from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

from src.app.domain.reports.service import ReportService


def _aggregate_snapshot() -> dict:
    return {
        "season": "2025-26",
        "gameweek": 31,
        "expert_count": 0,
        "player_consensus": [],
        "captaincy_consensus": [],
        "transfer_consensus": [],
        "fixture_insights": [],
        "chip_strategy_consensus": [],
        "disagreements": {},
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
    }


def test_legacy_lineup_is_adapted_without_mutating_the_stored_snapshot() -> None:
    positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    stored_final = {
        "season": "2025-26",
        "gameweek": 31,
        "overview": "Historical report",
        "conclusion": "Historical conclusion",
        "suggested_team": {
            "constructionStatus": "consensus",
            "formation": "3-4-3",
            "startingXi": [
                {
                    "playerId": index,
                    "name": f"Player {index}",
                    "position": position,
                }
                for index, position in enumerate(positions, start=1)
            ],
        },
    }
    original = deepcopy(stored_final)
    row = SimpleNamespace(
        run_id="legacy-run",
        final_report=stored_final,
        aggregate_report=_aggregate_snapshot(),
        updated_at=datetime.now(timezone.utc),
    )

    bundle = ReportService._bundle(row)

    team = bundle.final_report.suggested_team
    assert team is not None
    assert team.constructionMethod == "legacy_snapshot"
    assert team.consensusStrength == "insufficient"
    assert team.provenanceAvailable is False
    assert team.provenance is None
    assert team.startingXi[0].support is None
    assert stored_final == original
