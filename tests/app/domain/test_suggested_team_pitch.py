from __future__ import annotations

from src.app.domain.reports.suggested_team import (
    build_explicit_position_catalog,
    build_suggested_team_from_reveals,
)
from src.schemas.aggregate_report import ExpertTeamRevealItem


def _reveal(*, annotated: bool = True) -> ExpertTeamRevealItem:
    positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    names = [f"Player {index}" for index in range(1, 12)]
    current_team = (
        [f"{name} {position}" for name, position in zip(names, positions, strict=True)]
        if annotated
        else names
    )
    return ExpertTeamRevealItem(
        expert_name="Complete expert",
        video_title="Team reveal",
        current_team=current_team,
        starting_xi=names,
        captain="Player 9",
        vice_captain="Player 5",
        confidence=0.9,
    )


def test_builds_pitch_team_only_from_explicit_position_annotations() -> None:
    team = build_suggested_team_from_reveals([_reveal()])

    assert team is not None
    assert team.formation == "3-4-3"
    assert len(team.startingXi) == 11
    assert [player.position for player in team.startingXi[:4]] == [
        "GK",
        "DEF",
        "DEF",
        "DEF",
    ]
    assert team.startingXi[8].captain is True
    assert team.startingXi[4].viceCaptain is True
    assert len({player.playerId for player in team.startingXi}) == 11


def test_rejects_unannotated_or_incomplete_reveals() -> None:
    assert build_suggested_team_from_reveals([_reveal(annotated=False)]) is None

    incomplete = _reveal()
    incomplete.starting_xi.pop()
    assert build_suggested_team_from_reveals([incomplete]) is None


def test_reuses_only_explicit_positions_from_another_saved_run() -> None:
    annotated = _reveal()
    catalog = build_explicit_position_catalog([annotated])
    unannotated = _reveal(annotated=False)

    team = build_suggested_team_from_reveals([unannotated], catalog)

    assert team is not None
    assert team.formation == "3-4-3"


def test_builds_pitch_team_from_structured_player_positions() -> None:
    reveal = _reveal(annotated=False)
    positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    reveal.player_positions = dict(
        zip(reveal.starting_xi, positions, strict=True)
    )

    team = build_suggested_team_from_reveals([reveal])

    assert team is not None
    assert team.formation == "3-4-3"
    assert [player.position for player in team.startingXi] == positions


def test_discards_conflicting_position_metadata() -> None:
    first = _reveal()
    second = _reveal()
    second.current_team[0] = "Player 1 DEF"

    catalog = build_explicit_position_catalog([first, second])

    assert "player 1" not in catalog
