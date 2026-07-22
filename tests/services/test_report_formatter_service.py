from __future__ import annotations

from src.schemas.aggregate_report import (
    ConditionalAdviceItem,
    ConsensusItem,
    DisagreementReport,
    FixtureInsightConsensusItem,
    TransferConsensusItem,
)
from src.schemas.final_report import FinalExpertTeamReveal, FinalGameweekReport, FinalRecommendation
from src.services.report_formatter_service import (
    format_gameweek_markdown_report,
    rank_captaincy_insights,
    rank_transfer_insights,
)


def _build_aggregate_report():
    from src.schemas.final_report import AggregatedFPLReport

    return AggregatedFPLReport(
        season="2025-26",
        gameweek=32,
        expert_count=3,
        player_consensus=[],
        captaincy_consensus=[
            ConsensusItem(
                item="Bruno Fernandes Top Pick",
                mention_count=2,
                average_confidence=0.9,
                supporting_experts=["Expert A", "Expert B"],
            ),
            ConsensusItem(
                item="Bruno Man Utd",
                mention_count=1,
                average_confidence=0.8,
                supporting_experts=["Expert C"],
            ),
            ConsensusItem(
                item="Erling Haaland",
                mention_count=1,
                average_confidence=0.7,
                supporting_experts=["Expert B"],
            ),
        ],
        transfer_consensus=[
            TransferConsensusItem(
                player_name="Semenyo",
                direction="buy",
                mention_count=2,
                average_confidence=0.9,
                supporting_experts=["Expert A", "Expert B"],
            ),
            TransferConsensusItem(
                player_name="Antoine Semenyo",
                direction="buy",
                mention_count=1,
                average_confidence=0.8,
                supporting_experts=["Expert C"],
            ),
        ],
        fixture_insights=[
            FixtureInsightConsensusItem(
                insight="Arsenal assets can be deprioritized this week.",
                mention_count=2,
                supporting_experts=["Expert A", "Expert B"],
            )
        ],
        chip_strategy_consensus=[
            ConsensusItem(
                item="WC32 -> BB33 -> FH34",
                mention_count=2,
                average_confidence=0.8,
                supporting_experts=["Expert A", "Expert C"],
            )
        ],
        disagreements=DisagreementReport(),
        conditional_advice=[
            ConditionalAdviceItem(
                expert_name="Expert A",
                text="Ekitike carries a minutes risk.",
                reason="rotation",
            )
        ],
        wait_for_news=["Late Liverpool team news"],
    )


def _build_final_report() -> FinalGameweekReport:
    return FinalGameweekReport(
        season="2025-26",
        gameweek=32,
        overview="Aggregated input from 3 expert sources produced clear signals this week.",
        transfers=[FinalRecommendation(title="Buy Semenyo", rationale="Consensus", confidence=0.9)],
        captaincy=[
            FinalRecommendation(title="Bruno Fernandes", rationale="Consensus", confidence=0.9),
            FinalRecommendation(title="Bruno Man Utd", rationale="Duplicate form", confidence=0.8),
        ],
        chip_strategy=[
            FinalRecommendation(title="WC32 -> BB33 -> FH34", rationale="Consensus", confidence=0.8)
        ],
        fixture_notes=["Arsenal assets can be deprioritized this week."],
        disagreements=[],
        conditional_advice=["Ekitike carries a minutes risk."],
        wait_for_news=["Late Liverpool team news"],
        expert_team_reveals=[
            FinalExpertTeamReveal(
                expert_name="Expert A",
                summary="Moves in: Bruno Fernandes; out: Ollie Watkins. Captain Mohamed Salah.",
                captain="Mohamed Salah",
                transfers_in=["Bruno Fernandes"],
                transfers_out=["Ollie Watkins"],
                confidence=1.0,
            )
        ],
        conclusion="Stay flexible and avoid forcing marginal moves.",
    )


def test_rank_captaincy_insights_collapses_duplicate_player_mentions() -> None:
    ranked = rank_captaincy_insights(_build_aggregate_report(), _build_final_report())

    assert ranked[0].title == "Bruno Fernandes"
    assert ranked[0].mention_count == 3
    assert ranked[1].title == "Erling Haaland"


def test_rank_transfer_insights_collapses_duplicate_player_mentions() -> None:
    ranked = rank_transfer_insights(_build_aggregate_report(), _build_final_report())

    assert ranked == [
        ranked[0],
    ]
    assert ranked[0].title == "Buy Antoine Semenyo"
    assert ranked[0].mention_count == 3


def test_markdown_report_renders_expected_sections() -> None:
    markdown = format_gameweek_markdown_report(_build_aggregate_report(), _build_final_report())

    assert markdown.startswith("## GW32 FPL Expert Summary")
    assert "### Captaincy" in markdown
    assert "1. Bruno Fernandes" in markdown
    assert "### Transfers" in markdown
    assert "- Buy Antoine Semenyo" in markdown
    assert "### Risks" in markdown
    assert "- Late Liverpool team news" in markdown
    assert "### Expert Team Reveals" in markdown
    assert "- Expert A: Moves in: Bruno Fernandes; out: Ollie Watkins. Captain Mohamed Salah." in markdown
    assert "### Conclusion" in markdown


def test_markdown_report_handles_empty_input() -> None:
    from src.schemas.final_report import AggregatedFPLReport

    aggregate_report = AggregatedFPLReport(
        season="2025-26",
        gameweek=32,
        expert_count=0,
        player_consensus=[],
        captaincy_consensus=[],
        transfer_consensus=[],
        fixture_insights=[],
        chip_strategy_consensus=[],
        disagreements=DisagreementReport(),
        conditional_advice=[],
        wait_for_news=[],
    )
    final_report = FinalGameweekReport(
        season="2025-26",
        gameweek=32,
        overview="Not enough data yet.",
        transfers=[],
        captaincy=[],
        chip_strategy=[],
        fixture_notes=[],
        disagreements=[],
        conditional_advice=[],
        wait_for_news=[],
        conclusion="Wait for more input.",
    )

    markdown = format_gameweek_markdown_report(aggregate_report, final_report)

    assert markdown == (
        "## GW32 FPL Expert Summary\n\n"
        "Not enough data yet.\n\n"
        "### Conclusion\n"
        "Wait for more input.\n"
    )
