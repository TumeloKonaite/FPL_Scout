from __future__ import annotations

from src.schemas.aggregate_report import DisagreementReport
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.services.aggregation_service import build_aggregated_fpl_report
from src.services.synthesis_service import build_fallback_final_report


def _build_analysis(
    expert_name: str,
    *,
    recommended_players: list[str] | None = None,
    captaincy_picks: list[str] | None = None,
    reasoning: list[str] | None = None,
    key_takeaways: list[str] | None = None,
) -> ExpertVideoAnalysis:
    return ExpertVideoAnalysis(
        expert_name=expert_name,
        video_title=f"{expert_name} GW33",
        gameweek=33,
        summary="Sparse analysis",
        key_takeaways=key_takeaways or [],
        recommended_players=recommended_players or [],
        avoid_players=[],
        captaincy_picks=captaincy_picks or [],
        chip_strategy=None,
        reasoning=reasoning or [],
        confidence="medium",
    )


def test_aggregation_dedupes_duplicate_analysis_content() -> None:
    analysis = _build_analysis("Expert A", recommended_players=["Saka"], captaincy_picks=["Salah"])

    report = build_aggregated_fpl_report([analysis, analysis.model_copy()], season="2025-26", gameweek=33)

    assert report.expert_count == 1
    assert report.player_consensus[0].mention_count == 1
    assert report.captaincy_consensus[0].mention_count == 1


def test_fallback_report_handles_empty_sections_without_broken_phrasing() -> None:
    report = AggregatedFPLReport(
        season="2025-26",
        gameweek=33,
        expert_count=2,
        player_consensus=[],
        captaincy_consensus=[],
        transfer_consensus=[],
        fixture_insights=[],
        chip_strategy_consensus=[],
        disagreements=DisagreementReport(),
        conditional_advice=[],
        wait_for_news=[],
    )

    final_report = build_fallback_final_report(report)

    assert isinstance(final_report, FinalGameweekReport)
    assert final_report.transfers == []
    assert final_report.captaincy == []
    assert "sparse" in final_report.overview
    assert "No strong consensus emerged" in final_report.conclusion


def test_sparse_structured_input_still_keeps_conditional_advice() -> None:
    analyses = [
        _build_analysis(
            "Expert A",
            reasoning=["If Saka is fit after the press conference, he becomes the standout move."],
        )
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=33)

    assert report.conditional_advice
    assert report.wait_for_news == ["Bukayo Saka"]
