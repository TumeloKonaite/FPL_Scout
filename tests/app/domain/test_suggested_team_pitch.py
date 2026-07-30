from __future__ import annotations

from src.app.domain.reports.suggested_team import (
    CataloguePlayer,
    ConsensusPolicy,
    PlayerCatalogue,
    build_explicit_position_catalog,
    construct_consensus_squad,
    _consensus_strength,
)
from src.schemas.aggregate_report import ExpertTeamRevealItem
from src.schemas.final_report import PlayerSupport, SuggestedPlayer


def _catalogue() -> PlayerCatalogue:
    positions = ["GK"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3
    return PlayerCatalogue(
        (
            CataloguePlayer(
                index,
                f"Player {index}",
                position,
                player_code=220000 + index,
                team_code=40 + (index % 2),
                photo=f"{220000 + index}.jpg",
            )
            for index, position in enumerate(positions, start=1)
        ),
        season="2025-26",
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
    assert all(player.playerCode != player.officialPlayerId for player in team.players or [])
    assert all(
        player.imageUrl
        == (
            "https://resources.premierleague.com/premierleague/"
            f"photos/players/110x140/p{player.playerCode}.png"
        )
        for player in team.players or []
    )
    assert all(
        player.teamBadgeUrl
        == (
            "https://resources.premierleague.com/premierleague/"
            f"badges/50/t{player.teamCode}.png"
        )
        for player in team.players or []
    )
    assert team.constructionMethod == "vote_based_consensus"
    assert team.consensusStrength == "moderate"
    assert team.eligibleRevealCount == 2
    assert team.eligibleExpertCount == 2
    assert team.provenance is not None
    assert team.provenance.generatedAt.endswith("Z")
    assert team.provenance.formationDerivation.formation == team.formation
    assert team.provenance.formationDerivation.authoritativeCataloguePositions
    assert team.provenance.consensusStrengthBasis.medianSupportPercentage == 100
    assert all(player.support is not None for player in team.players or [])


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
    assert team.eligibleExpertCount == 2
    assert player.support is not None
    assert player.support.starterSupportCount == 2
    assert player.support.starterSupportPercentage == 100
    assert player.support.captainSupportCount == 2
    assert player.support.viceCaptainSupportCount == 0
    assert team.provenance is not None
    assert team.provenance.contributingRevealCount == 3
    assert team.provenance.contributingExpertCount == 2
    assert team.provenance.excludedRevealCount == 0
    assert player.contributingRevealIds == [
        "alpha-second",
        "alpha-source",
        "bravo-source",
    ]


def test_requires_authoritative_catalogue_and_classifies_one_expert_safely() -> None:
    missing = construct_consensus_squad([_reveal("alpha", (3, 4, 3))], None)
    one_expert = construct_consensus_squad(
        [_reveal("alpha", (3, 4, 3))],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert missing.failureReason == "authoritative_player_catalogue_unavailable"
    assert one_expert.failureReason == "insufficient_contributing_experts"
    assert one_expert.constructionMethod == "insufficient_evidence"
    assert one_expert.consensusStrength == "insufficient"
    assert one_expert.eligibleExpertCount == 1
    assert one_expert.synthesisDiagnostics["requiredExpertCount"] == 2
    assert one_expert.synthesisDiagnostics["actualContributingExpertCount"] == 1


def test_partial_reveals_merge_and_dedupe_votes_per_expert_player() -> None:
    alpha_first = _reveal("alpha", (3, 4, 3)).model_copy(
        update={
            "source_id": "alpha-first",
            "current_team": [f"Player {index}" for index in range(1, 9)],
            "starting_xi": [f"Player {index}" for index in range(1, 9)],
            "bench": [],
            "captain": "Player 8",
            "vice_captain": None,
        }
    )
    alpha_second = _reveal("alpha", (3, 4, 3)).model_copy(
        update={
            "source_id": "alpha-second",
            "current_team": [f"Player {index}" for index in range(8, 16)],
            "starting_xi": [f"Player {index}" for index in range(8, 16)],
            "bench": [],
            "captain": "Player 13",
            "vice_captain": "Player 8",
        }
    )

    team = construct_consensus_squad(
        [alpha_first, alpha_second, _reveal("bravo", (3, 4, 3))],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert team.constructionStatus == "consensus"
    assert team.eligibleRevealCount == 3
    assert team.contributingRevealCount == 3
    assert team.contributingExpertCount == 2
    overlapping = next(player for player in team.players or [] if player.playerId == 8)
    later_only = next(player for player in team.players or [] if player.playerId == 15)
    assert overlapping.expertSupportCount == 2
    assert later_only.expertSupportCount == 2
    assert overlapping.contributingRevealIds == [
        "alpha-first",
        "alpha-second",
        "bravo-source",
    ]


def test_one_player_partial_reveal_is_eligible() -> None:
    partial = _reveal("alpha", (3, 4, 3)).model_copy(
        update={
            "current_team": ["Player 1", "Unknown Player"],
            "starting_xi": [],
            "bench": [],
            "captain": None,
            "vice_captain": None,
        }
    )

    team = construct_consensus_squad(
        [partial],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert team.failureReason == "insufficient_contributing_experts"
    assert team.eligibleRevealCount == 1
    assert team.eligibleExpertCount == 1
    assert any(
        event.status in {"unresolved", "ambiguous", "rejected"}
        for event in team.resolutionDiagnostics
    )


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


def test_three_matching_experts_produce_strong_auditable_agreement() -> None:
    team = construct_consensus_squad(
        [
            _reveal("alpha", (3, 4, 3)),
            _reveal("bravo", (3, 4, 3)),
            _reveal("charlie", (3, 4, 3)),
        ],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert team.consensusStrength == "strong"
    assert team.provenance is not None
    assert team.provenance.consensusStrength == "strong"
    assert (
        team.provenance.consensusStrengthBasis.metric
        == "median_starting_xi_support_percentage"
    )
    assert team.provenance.consensusStrengthBasis.medianSupportPercentage == 100


def test_reveal_exclusions_are_persisted_and_do_not_change_vote_denominator() -> None:
    missing_identity = _reveal("missing", (3, 4, 3)).model_copy(
        update={"expert_id": None, "source_id": "missing-id"}
    )
    wrong_season = _reveal("old", (3, 4, 3)).model_copy(
        update={"season": "2024-25", "source_id": "old-season"}
    )
    wrong_gameweek = _reveal("future", (3, 4, 3)).model_copy(
        update={"gameweek": 32, "source_id": "wrong-gw"}
    )
    empty = _reveal("empty", (3, 4, 3)).model_copy(
        update={
            "source_id": "empty",
            "current_team": [],
            "starting_xi": [],
            "bench": [],
            "captain": None,
            "vice_captain": None,
        }
    )
    duplicate_source = _reveal("charlie", (3, 4, 3)).model_copy(
        update={"source_id": "alpha-source"}
    )

    team = construct_consensus_squad(
        [
            _reveal("alpha", (3, 4, 3)),
            _reveal("bravo", (3, 4, 3)),
            missing_identity,
            wrong_season,
            wrong_gameweek,
            empty,
            duplicate_source,
        ],
        _catalogue(),
        ConsensusPolicy(season="2025-26", gameweek=31),
    )

    assert team.eligibleRevealCount == 2
    assert team.eligibleExpertCount == 2
    assert team.provenance is not None
    reasons = {
        reason
        for excluded in team.provenance.excludedReveals
        for reason in excluded.reasons
    }
    assert reasons == {
        "missing_expert_identity",
        "wrong_season",
        "wrong_gameweek",
        "empty_resolved_squad",
        "duplicate_source",
    }
    assert all(
        player.support is not None
        and player.support.eligibleExpertCount == 2
        for player in team.players or []
    )


def test_split_strength_uses_deterministic_median_starter_support() -> None:
    starters = [
        SuggestedPlayer(
            playerId=index,
            name=f"Player {index}",
            position="GK" if index == 1 else "DEF",
            support=PlayerSupport(
                eligibleExpertCount=3,
                starterSupportCount=1,
                starterSupportPercentage=33.3,
                squadSupportCount=1,
                squadSupportPercentage=33.3,
                captainSupportCount=0,
                captainSupportPercentage=0,
                viceCaptainSupportCount=0,
                viceCaptainSupportPercentage=0,
                contributingExpertIds=["alpha"],
            ),
        )
        for index in range(1, 12)
    ]

    strength, basis = _consensus_strength(
        starters,
        eligible_expert_count=3,
        valid_lineup=True,
        construction_method="vote_based_consensus",
    )

    assert strength == "split"
    assert basis.medianSupportPercentage == 33.3
