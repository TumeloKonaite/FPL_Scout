from __future__ import annotations

from src.app.domain.reports.suggested_team import (
    CataloguePlayer,
    ConsensusPolicy,
    PlayerCatalogue,
    build_explicit_position_catalog,
    construct_consensus_squad,
)
from src.schemas.aggregate_report import ExpertTeamRevealItem


def _catalogue() -> PlayerCatalogue:
    positions = ["GK"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3
    return PlayerCatalogue(
        CataloguePlayer(index, f"Player {index}", position)
        for index, position in enumerate(positions, start=1)
    )


def _reveal(expert_id: str, formation: tuple[int, int, int]) -> ExpertTeamRevealItem:
    defenders, midfielders, forwards = formation
    starters = [
        "Player 1",
        *[f"Player {index}" for index in range(3, 3 + defenders)],
        *[f"Player {index}" for index in range(8, 8 + midfielders)],
        *[f"Player {index}" for index in range(13, 13 + forwards)],
    ]
    all_players = [f"Player {index}" for index in range(1, 16)]
    return ExpertTeamRevealItem(
        expert_name=expert_id.upper(),
        expert_id=expert_id,
        source_id=f"{expert_id}-source",
        video_title="Team reveal",
        season="2025-26",
        gameweek=31,
        current_team=all_players,
        starting_xi=starters,
        bench=[name for name in all_players if name not in starters],
        captain="Player 13",
        vice_captain="Player 8",
        confidence=0.9,
    )


def test_constructs_vote_based_full_squad_from_authoritative_catalogue() -> None:
    team = construct_consensus_squad(
        [_reveal("alpha", (3, 4, 3)), _reveal("bravo", (4, 4, 2))],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert team.constructionStatus == "consensus"
    assert len(team.startingXi) == 11
    assert len(team.bench) == 4
    assert len({player.officialPlayerId for player in team.players or []}) == 15
    assert team.captainPlayerId == 13
    assert team.viceCaptainPlayerId == 8
    assert all(player.officialPlayerId == player.playerId for player in team.players or [])


def test_repeated_and_multi_reveal_votes_are_deduplicated_by_expert() -> None:
    first = _reveal("alpha", (3, 4, 3))
    first.starting_xi.append("Player 13")
    second = first.model_copy(
        deep=True,
        update={"source_id": "alpha-second", "confidence": 0.4},
    )
    team = construct_consensus_squad(
        [second, _reveal("bravo", (3, 4, 3)), first],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    player = next(item for item in team.startingXi if item.playerId == 13)
    assert player.starterSupport == 2
    assert player.captainSupport == 2
    assert player.confidenceSum == 1.8
    assert player.contributingExpertIds == ["alpha", "bravo"]
    assert team.eligibleRevealCount == 3


def test_requires_authoritative_catalogue_and_two_stable_experts() -> None:
    missing = construct_consensus_squad([_reveal("alpha", (3, 4, 3))], None)
    one_expert = construct_consensus_squad(
        [_reveal("alpha", (3, 4, 3))],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert missing.failureReason == "authoritative_player_catalogue_unavailable"
    assert one_expert.failureReason == "fewer_than_two_eligible_experts"


def test_missing_captaincy_uses_only_the_configured_fallback() -> None:
    reveals = [_reveal("alpha", (3, 4, 3)), _reveal("bravo", (3, 4, 3))]
    for reveal in reveals:
        reveal.captain = None
        reveal.vice_captain = None

    required = construct_consensus_squad(reveals, _catalogue())
    fallback = construct_consensus_squad(
        reveals,
        _catalogue(),
        ConsensusPolicy(captaincy_fallback="starter_support"),
    )

    assert required.failureReason == "insufficient_captaincy_evidence"
    assert fallback.constructionStatus == "consensus"
    assert fallback.captainPlayerId in {
        player.playerId for player in fallback.startingXi
    }


def test_input_order_and_expert_display_names_do_not_change_selection() -> None:
    alpha = _reveal("alpha", (3, 4, 3))
    bravo = _reveal("bravo", (4, 4, 2))
    first = construct_consensus_squad([alpha, bravo], _catalogue())
    alpha.expert_name = "ZZZ"
    bravo.expert_name = "AAA"
    second = construct_consensus_squad([bravo, alpha], _catalogue())

    assert first.formation == second.formation
    assert [item.playerId for item in first.startingXi] == [
        item.playerId for item in second.startingXi
    ]
    assert first.captainPlayerId == second.captainPlayerId
    assert first.viceCaptainPlayerId == second.viceCaptainPlayerId


def test_legacy_annotations_are_not_an_authoritative_catalogue() -> None:
    reveal = _reveal("alpha", (3, 4, 3))
    reveal.player_positions = {"Player 1": "GK"}

    annotations = build_explicit_position_catalog([reveal])
    result = construct_consensus_squad([reveal], None)

    assert annotations == {"player 1": "GK"}
    assert result.constructionStatus == "insufficient_evidence"
