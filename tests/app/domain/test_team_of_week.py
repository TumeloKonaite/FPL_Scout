from __future__ import annotations

from src.app.domain.reports.team_of_week import (
    PlayerCandidate,
    TeamConstraints,
    build_suggested_team_of_week,
    rank_players,
)
from src.schemas.aggregate_report import ExpertTeamRevealItem


def _reveal(
    expert_name: str,
    starting_xi: list[str],
    bench: list[str],
    captain: str | None = None,
    vice: str | None = None,
) -> ExpertTeamRevealItem:
    return ExpertTeamRevealItem(
        expert_name=expert_name,
        video_title=f"{expert_name} video",
        starting_xi=starting_xi,
        bench=bench,
        captain=captain,
        vice_captain=vice,
    )


def test_build_suggested_team_of_week_picks_most_common_players() -> None:
    team = build_suggested_team_of_week(
        [
            _reveal(
                "A",
                ["Gk1", "D1", "D2", "D3", "M1", "M2", "M3", "M4", "F1", "F2", "F3"],
                ["B1", "B2", "B3", "B4"],
                captain="M1",
                vice="F1",
            ),
            _reveal(
                "B",
                ["Gk1", "D1", "D2", "D4", "M1", "M2", "M5", "M4", "F1", "F2", "F4"],
                ["B1", "B5", "B3", "B6"],
                captain="M1",
                vice="F2",
            ),
            _reveal(
                "C",
                ["Gk1", "D1", "D2", "D3", "M1", "M2", "M3", "M6", "F1", "F2", "F5"],
                ["B1", "B2", "B7", "B8"],
                captain="F1",
                vice="F2",
            ),
        ]
    )

    assert team is not None
    assert team.starting_xi[:6] == ["D1", "D2", "F1", "F2", "Gk1", "M1"]
    assert len(team.starting_xi) == 11
    assert team.bench == ["B1", "B2", "B3", "B4"]
    assert team.captain == "M1"
    assert team.vice_captain == "F2"


def test_build_suggested_team_of_week_merges_player_aliases() -> None:
    team = build_suggested_team_of_week(
        [
            _reveal(
                "A",
                ["Bruno", "Semenyo", "Haaland"],
                ["Palmer"],
                captain="Bruno",
                vice="Haaland",
            ),
            _reveal(
                "B",
                ["Bruno Fernandes", "Antoine Semenyo", "Erling Haaland"],
                ["Cole Palmer"],
                captain="Bruno Fernandes",
                vice="Erling Haaland",
            ),
        ]
    )

    assert team is not None
    assert "Bruno Fernandes" in team.starting_xi
    assert "Antoine Semenyo" in team.starting_xi
    assert "Erling Haaland" in team.starting_xi
    assert team.bench == ["Cole Palmer"]
    assert team.player_votes["Bruno Fernandes"] == 2
    assert team.captain == "Bruno Fernandes"
    assert team.vice_captain == "Erling Haaland"


def test_rank_players_returns_vote_order_with_metadata() -> None:
    ranked = rank_players(
        [
            _reveal("A", ["Saka", "Palmer"], []),
            _reveal("B", ["Bukayo Saka"], []),
        ],
        player_pool=[PlayerCandidate("Bukayo Saka", position="MID", price=9.8)],
    )

    assert ranked[0].name == "Bukayo Saka"
    assert ranked[0].votes == 2
    assert ranked[0].position == "MID"
    assert ranked[0].price == 9.8


def test_build_suggested_team_of_week_applies_budget_constraint() -> None:
    team = build_suggested_team_of_week(
        [
            _reveal("A", ["Premium", "Value", "Cheap"], []),
            _reveal("B", ["Premium", "Value", "Cheap"], []),
        ],
        player_pool=[
            PlayerCandidate("Premium", position="MID", price=10.0),
            PlayerCandidate("Value", position="MID", price=6.0),
            PlayerCandidate("Cheap", position="FWD", price=4.5),
        ],
        constraints=TeamConstraints(budget=10.5, max_players=3),
    )

    assert team is not None
    assert team.starting_xi == ["Cheap", "Value"]
    assert team.total_price == 10.5


def test_build_suggested_team_of_week_applies_position_constraint() -> None:
    team = build_suggested_team_of_week(
        [
            _reveal("A", ["Mid A", "Mid B", "Def A", "Def B"], []),
            _reveal("B", ["Mid A", "Mid B", "Def A", "Def B"], []),
        ],
        player_pool=[
            PlayerCandidate("Mid A", position="MID", price=7.0),
            PlayerCandidate("Mid B", position="MID", price=7.0),
            PlayerCandidate("Def A", position="DEF", price=5.0),
            PlayerCandidate("Def B", position="DEF", price=5.0),
        ],
        constraints=TeamConstraints(max_players=4, max_positions={"MID": 1}),
    )

    assert team is not None
    assert team.position_counts["MID"] == 1
    assert "Mid A" in team.starting_xi
    assert "Mid B" not in team.starting_xi


def test_build_suggested_team_of_week_handles_empty_or_missing_data() -> None:
    assert build_suggested_team_of_week([]) is None
    assert build_suggested_team_of_week(
        [_reveal("A", [], ["Bench"], captain="Cap", vice="Vice")]
    ) is None
