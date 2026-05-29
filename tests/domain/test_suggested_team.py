from __future__ import annotations

from src.app.domain.reports.team_of_week import (
    PlayerCandidate,
    TeamConstraints,
    build_suggested_team_of_week,
    normalize_team_player,
    rank_players,
)
from src.schemas.aggregate_report import ExpertTeamRevealItem


def _reveal(
    expert_name: str,
    starters: list[str],
    bench: list[str] | None = None,
    captain: str | None = None,
    vice: str | None = None,
) -> ExpertTeamRevealItem:
    return ExpertTeamRevealItem(
        expert_name=expert_name,
        video_title=f"{expert_name} reveal",
        starting_xi=starters,
        bench=bench or [],
        captain=captain,
        vice_captain=vice,
    )


def test_rank_players_normalizes_aliases_and_orders_by_votes() -> None:
    ranked = rank_players(
        [
            _reveal("A", ["Semenyo", "Saka"]),
            _reveal("B", ["Antoine Semenyo", "Bukayo Saka"]),
            _reveal("C", ["Semenyo"]),
        ],
        player_pool=[
            PlayerCandidate("Antoine Semenyo", position="MID", price=7.8),
            PlayerCandidate("Bukayo Saka", position="MID", price=10.1),
        ],
    )

    assert ranked[0].name == "Antoine Semenyo"
    assert ranked[0].votes == 3
    assert ranked[0].position == "MID"
    assert ranked[1].name == "Bukayo Saka"
    assert normalize_team_player("semeno") == "antoine semenyo"


def test_suggested_team_applies_budget_and_position_constraints() -> None:
    team = build_suggested_team_of_week(
        [
            _reveal("A", ["Premium Mid", "Value Def", "Value Fwd"]),
            _reveal("B", ["Premium Mid", "Value Def", "Value Fwd"]),
        ],
        player_pool=[
            PlayerCandidate("Premium Mid", position="MID", price=11.0),
            PlayerCandidate("Value Def", position="DEF", price=4.5),
            PlayerCandidate("Value Fwd", position="FWD", price=6.0),
        ],
        constraints=TeamConstraints(
            budget=10.5,
            max_players=3,
            min_positions={"DEF": 1, "FWD": 1},
        ),
    )

    assert team is not None
    assert team.starting_xi == ["Value Def", "Value Fwd"]
    assert team.total_price == 10.5
    assert team.position_counts == {"DEF": 1, "FWD": 1}


def test_suggested_team_returns_none_when_no_starter_votes_exist() -> None:
    team = build_suggested_team_of_week(
        [_reveal("A", [], ["Bench Option"], captain="Captain")]
    )

    assert team is None
