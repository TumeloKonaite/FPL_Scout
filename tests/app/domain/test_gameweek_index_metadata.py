from __future__ import annotations

from src.app.domain.reports.index_metadata import public_gameweek_index_metadata


def _player(player_id: int, position: str) -> dict[str, object]:
    return {
        "playerId": player_id,
        "officialPlayerId": player_id,
        "name": f"Player {player_id}",
        "position": position,
    }


def _valid_team() -> dict[str, object]:
    starter_positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    bench_positions = ["GK", "DEF", "DEF", "MID"]
    starters = [
        _player(player_id, position)
        for player_id, position in enumerate(starter_positions, start=1)
    ]
    bench = [
        _player(player_id, position)
        for player_id, position in enumerate(bench_positions, start=12)
    ]
    return {
        "constructionStatus": "consensus",
        "constructionMethod": "vote_based_consensus",
        "consensusStrength": "moderate",
        "failureReason": None,
        "formation": "3-4-3",
        "startingXi": starters,
        "bench": bench,
        "captainPlayerId": 1,
        "viceCaptainPlayerId": 2,
    }


def test_suggested_team_metadata_accepts_valid_and_legacy_snapshots() -> None:
    modern = _valid_team()
    legacy = dict(modern)
    legacy.pop("constructionMethod")
    legacy.pop("consensusStrength")

    report = {
        "season": "2025-26",
        "gameweek": 32,
        "overview": "Overview",
        "conclusion": "Conclusion",
    }

    assert public_gameweek_index_metadata(
        {**report, "suggested_team": modern}
    ).has_suggested_team is True
    assert public_gameweek_index_metadata(
        {**report, "suggested_team": legacy}
    ).has_suggested_team is True


def test_suggested_team_metadata_rejects_incomplete_or_failed_teams() -> None:
    incomplete = _valid_team()
    incomplete["bench"] = []
    failed = _valid_team()
    failed["constructionStatus"] = "insufficient_evidence"
    failed["failureReason"] = "not_enough_players"

    report = {
        "season": "2025-26",
        "gameweek": 32,
        "overview": "Overview",
        "conclusion": "Conclusion",
    }

    assert public_gameweek_index_metadata(
        {**report, "suggested_team": incomplete}
    ).has_suggested_team is False
    assert public_gameweek_index_metadata(
        {**report, "suggested_team": failed}
    ).has_suggested_team is False
    invalid = public_gameweek_index_metadata({"overview": "invalid report"})
    assert invalid.has_report is False
    assert invalid.has_suggested_team is False
