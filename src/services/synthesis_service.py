from __future__ import annotations

from src.app.domain.reports.suggested_team import build_suggested_team_from_reveals
from src.agents.final_synthesis_agent import run_final_synthesis
from src.schemas.final_report import (
    AggregatedFPLReport,
    FinalDisagreement,
    FinalExpertTeamReveal,
    FinalGameweekReport,
    FinalRecommendation,
)


def _build_empty_final_report(report: AggregatedFPLReport) -> FinalGameweekReport:
    return FinalGameweekReport(
        gameweek=report.gameweek,
        overview=(
            "There is not enough aggregated expert data yet to produce a confident final report. "
            "Treat this as a placeholder until more expert analysis is available."
        ),
        transfers=[],
        captaincy=[],
        chip_strategy=[],
        fixture_notes=[],
        disagreements=[],
        conditional_advice=[],
        wait_for_news=[],
        expert_team_reveals=[],
        conclusion="Wait for more expert input before making aggressive moves.",
    )


def build_fallback_final_report(report: AggregatedFPLReport) -> FinalGameweekReport:
    """Build a safe report when synthesis is unavailable or malformed."""
    if not report.expert_count:
        overview = "There is not enough aggregated expert data yet to produce a confident final report."
    else:
        available_sections = [
            label
            for label, items in (
                ("transfers", report.transfer_consensus),
                ("captaincy", report.captaincy_consensus),
                ("chip strategy", report.chip_strategy_consensus),
                ("fixture notes", report.fixture_insights),
            )
            if items
        ]
        if available_sections:
            overview = (
                f"Aggregated input from {report.expert_count} expert sources produced usable signals for "
                + ", ".join(available_sections[:-1] + [available_sections[-1]])
                + ", while preserving areas of uncertainty."
            )
        else:
            overview = (
                f"Aggregated input from {report.expert_count} expert sources was sparse, so this fallback report "
                "focuses on uncertainty, conditional advice, and what still needs monitoring."
            )

    transfers = [
        FinalRecommendation(
            title=f"{item.direction.title()} {item.player_name}",
            rationale=(
                f"Mentioned by {item.mention_count} expert(s): "
                + ", ".join(item.supporting_experts)
            ),
            confidence=item.average_confidence,
        )
        for item in report.transfer_consensus[:3]
    ]
    captaincy = [
        FinalRecommendation(
            title=item.item,
            rationale=(
                f"Backed by {item.mention_count} expert(s): "
                + ", ".join(item.supporting_experts)
            ),
            confidence=item.average_confidence,
        )
        for item in report.captaincy_consensus[:2]
    ]
    chip_strategy = [
        FinalRecommendation(
            title=item.item,
            rationale=(
                f"Supported by {item.mention_count} expert(s): "
                + ", ".join(item.supporting_experts)
            ),
            confidence=item.average_confidence,
        )
        for item in report.chip_strategy_consensus[:2]
    ]
    disagreements = [
        FinalDisagreement(
            topic=f"Player split: {item.player}",
            summary=(
                f"Some experts support {item.player} while others advise against the move."
            ),
            sides=[
                f"Positive: {', '.join(item.positive_experts)}",
                f"Negative: {', '.join(item.negative_experts)}",
            ],
        )
        for item in report.disagreements.players
    ]
    expert_team_reveals = [
        FinalExpertTeamReveal(
            expert_name=item.expert_name,
            summary=_build_team_reveal_summary(item),
            captain=item.captain,
            vice_captain=item.vice_captain,
            transfers_in=item.transfers_in,
            transfers_out=item.transfers_out,
            confidence=item.confidence,
        )
        for item in report.expert_team_reveals[:3]
    ]

    conclusion_parts: list[str] = []
    if transfers or captaincy or chip_strategy:
        conclusion_parts.append("Use the strongest consensus signals that are actually supported this week.")
    else:
        conclusion_parts.append("No strong consensus emerged from the structured input this week.")
    if report.wait_for_news:
        conclusion_parts.append("Monitor late team news before the deadline.")
    else:
        conclusion_parts.append("Stay flexible and avoid forcing marginal moves.")

    final_report = FinalGameweekReport(
        gameweek=report.gameweek,
        overview=overview,
        transfers=transfers,
        captaincy=captaincy,
        chip_strategy=chip_strategy,
        fixture_notes=[item.insight for item in report.fixture_insights[:3]],
        disagreements=disagreements,
        conditional_advice=[item.text for item in report.conditional_advice[:3]],
        wait_for_news=report.wait_for_news,
        expert_team_reveals=expert_team_reveals,
        conclusion=" ".join(conclusion_parts),
    )
    return _attach_suggested_team(final_report, report)


def _attach_suggested_team(
    final_report: FinalGameweekReport,
    aggregate_report: AggregatedFPLReport,
) -> FinalGameweekReport:
    if final_report.suggested_team is not None:
        return final_report
    return final_report.model_copy(
        update={
            "suggested_team": build_suggested_team_from_reveals(
                aggregate_report.expert_team_reveals
            )
        }
    )


def _build_team_reveal_summary(item) -> str:
    summary_parts: list[str] = []
    if item.transfers_in or item.transfers_out:
        moves: list[str] = []
        if item.transfers_in:
            moves.append("in: " + ", ".join(item.transfers_in))
        if item.transfers_out:
            moves.append("out: " + ", ".join(item.transfers_out))
        summary_parts.append("Moves " + "; ".join(moves))
    if item.captain:
        captain_text = f"Captain {item.captain}"
        if item.vice_captain:
            captain_text += f", vice {item.vice_captain}"
        summary_parts.append(captain_text)
    if item.starting_xi:
        summary_parts.append("Starting XI core: " + ", ".join(item.starting_xi[:5]))
    elif item.current_team:
        summary_parts.append("Draft core: " + ", ".join(item.current_team[:5]))
    elif item.bench:
        summary_parts.append("Bench includes " + ", ".join(item.bench[:3]))
    return ". ".join(summary_parts) or "Expert discussed a draft team for the week."


async def synthesize_final_report(report: AggregatedFPLReport) -> FinalGameweekReport:
    """Convert aggregated FPL data into a polished final gameweek report."""
    if report.expert_count == 0:
        return _build_empty_final_report(report)

    try:
        return _attach_suggested_team(await run_final_synthesis(report), report)
    except Exception:
        return build_fallback_final_report(report)
