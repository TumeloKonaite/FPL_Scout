from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.schemas.aggregate_report import (
    CaptaincyDisagreementItem,
    ConditionalAdviceItem,
    ConsensusItem,
    DisagreementReport,
    ExpertTeamRevealItem,
    FixtureInsightConsensusItem,
    PlayerDisagreementItem,
    StrategyDisagreementItem,
    TransferConsensusItem,
)
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.agents.final_synthesis_agent import format_aggregated_report_input
from src.schemas.final_report import FinalDisagreement, FinalRecommendation
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.services.aggregation_service import build_aggregated_fpl_report
from src.services.synthesis_service import build_fallback_final_report, synthesize_final_report


def _build_aggregated_report() -> AggregatedFPLReport:
    return AggregatedFPLReport(
        gameweek=31,
        expert_count=3,
        player_consensus=[
            ConsensusItem(
                item="Bukayo Saka",
                mention_count=3,
                average_confidence=0.8889,
                supporting_experts=["Expert A", "Expert B", "Expert C"],
            )
        ],
        captaincy_consensus=[
            ConsensusItem(
                item="Mohamed Salah",
                mention_count=2,
                average_confidence=0.8333,
                supporting_experts=["Expert A", "Expert C"],
            )
        ],
        transfer_consensus=[
            TransferConsensusItem(
                player_name="Bukayo Saka",
                direction="buy",
                mention_count=3,
                average_confidence=0.8889,
                supporting_experts=["Expert A", "Expert B", "Expert C"],
            ),
            TransferConsensusItem(
                player_name="Ollie Watkins",
                direction="sell",
                mention_count=2,
                average_confidence=0.6667,
                supporting_experts=["Expert A", "Expert B"],
            ),
        ],
        fixture_insights=[
            FixtureInsightConsensusItem(
                insight="Arsenal have the standout fixture run over the next three gameweeks",
                mention_count=2,
                supporting_experts=["Expert A", "Expert B"],
            )
        ],
        chip_strategy_consensus=[
            ConsensusItem(
                item="wildcard",
                mention_count=2,
                average_confidence=0.8333,
                supporting_experts=["Expert A", "Expert C"],
            )
        ],
        disagreements=DisagreementReport(
            players=[
                PlayerDisagreementItem(
                    player="Erling Haaland",
                    positive_experts=["Expert A"],
                    negative_experts=["Expert B"],
                )
            ],
            captaincy=[
                CaptaincyDisagreementItem(
                    options=["Mohamed Salah", "Erling Haaland"],
                    expert_map={
                        "Mohamed Salah": ["Expert A", "Expert C"],
                        "Erling Haaland": ["Expert B"],
                    },
                )
            ],
            strategy=[
                StrategyDisagreementItem(
                    side_a="roll",
                    side_a_experts=["Expert B"],
                    side_b="buy_now",
                    side_b_experts=["Expert A"],
                )
            ],
        ),
        conditional_advice=[
            ConditionalAdviceItem(
                expert_name="Expert C",
                text="If Saka is declared fully fit, he becomes the top midfield buy.",
                reason="injury_update",
                related_entities=["Bukayo Saka"],
            )
        ],
        wait_for_news=["Bukayo Saka"],
        expert_team_reveals=[
            ExpertTeamRevealItem(
                expert_name="Expert A",
                video_title="Expert A GW31",
                current_team=["Mohamed Salah", "Bukayo Saka", "Bruno Fernandes"],
                starting_xi=["Mohamed Salah", "Bukayo Saka", "Bruno Fernandes"],
                bench=["Fabianski"],
                captain="Mohamed Salah",
                vice_captain="Bukayo Saka",
                transfers_in=["Bruno Fernandes"],
                transfers_out=["Ollie Watkins"],
                confidence=1.0,
            )
        ],
    )


def test_prompt_input_formatting_is_deterministic() -> None:
    report = _build_aggregated_report()

    first_render = format_aggregated_report_input(report)
    second_render = format_aggregated_report_input(report)

    assert first_render == second_render
    assert '"gameweek": 31' in first_render
    assert '"item": "Bukayo Saka"' in first_render
    assert '"wait_for_news": [' in first_render


def test_synthesize_final_report_returns_schema_valid_output() -> None:
    report = _build_aggregated_report()
    expected = FinalGameweekReport(
        gameweek=31,
        overview="The strongest expert consensus centers on buying Arsenal attackers, with Salah still edging captaincy while a few strategic splits remain.",
        transfers=[
            FinalRecommendation(
                title="Buy Bukayo Saka",
                rationale="Strong cross-expert backing makes him the standout attacking transfer.",
                confidence=0.89,
            ),
        ],
        captaincy=[
            FinalRecommendation(
                title="Mohamed Salah",
                rationale="He remains the safest captaincy route from the current consensus.",
                confidence=0.83,
            ),
        ],
        chip_strategy=[
            FinalRecommendation(
                title="Wildcard",
                rationale="There is enough support to keep wildcard discussions live for aggressive managers.",
                confidence=0.83,
            ),
        ],
        disagreements=[
            FinalDisagreement(
                topic="Captaincy split",
                summary="Captaincy is not unanimous, with one expert still backing Erling Haaland over Mohamed Salah.",
                sides=["Mohamed Salah", "Erling Haaland"],
            ),
        ],
        conditional_advice=[
            "If Saka is fully cleared in the latest injury update, he becomes the clearest midfield move.",
        ],
        wait_for_news=[
            "Monitor Bukayo Saka team news before locking in transfers.",
        ],
        expert_team_reveals=[],
        fixture_notes=[
            "Arsenal have the standout fixture run over the next three gameweeks.",
        ],
        conclusion="Prioritize the consensus core and leave room for late team news.",
    )

    mocked_run = AsyncMock(return_value=expected)

    with patch("src.services.synthesis_service.run_final_synthesis", mocked_run):
        result = asyncio.run(synthesize_final_report(report))

    assert result == expected
    validated = FinalGameweekReport.model_validate(result.model_dump())
    assert validated.conclusion == expected.conclusion
    mocked_run.assert_awaited_once()


def test_synthesize_final_report_short_circuits_empty_input() -> None:
    report = AggregatedFPLReport(
        gameweek=None,
        expert_count=0,
        player_consensus=[],
        captaincy_consensus=[],
        transfer_consensus=[],
        fixture_insights=[],
        chip_strategy_consensus=[],
        disagreements=DisagreementReport(),
        conditional_advice=[],
        wait_for_news=[],
        expert_team_reveals=[],
    )

    with patch("src.services.synthesis_service.run_final_synthesis", new_callable=AsyncMock) as mocked_run:
        result = asyncio.run(synthesize_final_report(report))

    assert result.gameweek is None
    assert result.transfers == []
    assert "not enough aggregated expert data" in result.overview
    mocked_run.assert_not_awaited()


def test_build_fallback_final_report_is_schema_valid() -> None:
    report = _build_aggregated_report()

    final_report = build_fallback_final_report(report)

    assert final_report.transfers[0].title == "Buy Bukayo Saka"
    assert final_report.captaincy[0].title == "Mohamed Salah"
    assert final_report.fixture_notes == [
        "Arsenal have the standout fixture run over the next three gameweeks"
    ]
    assert final_report.expert_team_reveals[0].expert_name == "Expert A"
    assert "Bruno Fernandes" in final_report.expert_team_reveals[0].summary
    validated = FinalGameweekReport.model_validate(final_report.model_dump())
    assert validated.wait_for_news == ["Bukayo Saka"]


def test_fallback_report_embeds_suggested_team_from_structured_positions() -> None:
    report = _build_aggregated_report()
    positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    names = [f"Player {index}" for index in range(1, 12)]
    report.expert_team_reveals = [
        ExpertTeamRevealItem(
            expert_name="Expert XI",
            video_title="Complete reveal",
            current_team=names,
            starting_xi=names,
            player_positions=dict(zip(names, positions, strict=True)),
            captain="Player 9",
            confidence=1.0,
        )
    ]

    final_report = build_fallback_final_report(report)

    assert final_report.suggested_team is not None
    assert final_report.suggested_team.formation == "3-4-3"
    assert len(final_report.suggested_team.startingXi) == 11


def test_synthesize_final_report_falls_back_when_agent_fails() -> None:
    report = _build_aggregated_report()

    with patch(
        "src.services.synthesis_service.run_final_synthesis",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ) as mocked_run:
        result = asyncio.run(synthesize_final_report(report))

    assert "Use the strongest consensus signals" in result.conclusion
    assert result.transfers
    mocked_run.assert_awaited_once()


def test_fallback_recommendations_publish_evidence_not_confidence() -> None:
    analysis = ExpertVideoAnalysis(
        expert_name="FPL Focal",
        video_title="GW31 captaincy",
        gameweek=31,
        summary="Salah captain",
        key_takeaways=[],
        recommended_players=[],
        avoid_players=[],
        captaincy_picks=["Salah"],
        reasoning=[],
        confidence="high",
        published_at="2026-07-20T12:00:00Z",
        source_url="https://example.com/captaincy",
    )
    aggregate = build_aggregated_fpl_report([analysis])

    recommendation = build_fallback_final_report(aggregate).captaincy[0]

    assert recommendation.confidence is None
    assert recommendation.consensus is not None
    assert recommendation.consensus.label == "strong"
    assert recommendation.consensus.supportCount == 1
    assert recommendation.consensus.relevantExpertCount == 1
    assert recommendation.sources[0].name == "FPL Focal"
    assert recommendation.freshness is not None
    assert recommendation.freshness.newestSourceAt == "2026-07-20T12:00:00+00:00"
