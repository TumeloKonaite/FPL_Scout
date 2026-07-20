from __future__ import annotations

from src.schemas.aggregate_report import (
    ConsensusItem,
    ExpertTeamRevealItem,
    FixtureInsightConsensusItem,
    TransferConsensusItem,
)
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport
from src.services.disagreement_service import (
    build_disagreement_report,
    extract_conditional_advice,
    extract_wait_for_news_entities,
)
from src.services.normalization import (
    canonical_chip_display,
    canonical_player_display,
    build_analysis_identity,
    normalize_chip_name,
    normalize_lookup_key,
    normalize_player_name,
    normalize_text_label,
    titleize_normalized,
)


_CONFIDENCE_TO_SCORE = {
    "low": 1 / 3,
    "medium": 2 / 3,
    "high": 1.0,
}


def _confidence_score(level: str) -> float:
    return _CONFIDENCE_TO_SCORE[level]


def _sorted_experts(experts: set[str]) -> list[str]:
    return sorted(experts, key=str.casefold)


def _unique_normalized_players(players: list[str]) -> set[str]:
    return {normalize_player_name(player) for player in players if normalize_player_name(player)}


def _unique_normalized_text(items: list[str]) -> set[str]:
    return {normalize_text_label(item) for item in items if normalize_text_label(item)}


def _canonicalize_player_like_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized_player = normalize_player_name(item)
        if normalized_player:
            display = canonical_player_display(normalized_player)
        else:
            display = titleize_normalized(normalize_text_label(item))
        if not display:
            continue
        key = normalize_lookup_key(display)
        if key in seen:
            continue
        seen.add(key)
        output.append(display)
    return output


def _canonicalize_player_positions(
    positions: dict[str, str],
) -> dict[str, str]:
    canonical: dict[str, str] = {}
    for name, position in positions.items():
        normalized = normalize_player_name(name)
        display = canonical_player_display(normalized) if normalized else ""
        if display:
            canonical[display] = position.upper()
    return canonical


def aggregate_expert_team_reveals(
    analyses: list[ExpertVideoAnalysis],
) -> list[ExpertTeamRevealItem]:
    reveals: list[ExpertTeamRevealItem] = []

    for analysis in sorted(analyses, key=lambda item: (item.expert_name.casefold(), item.video_title.casefold())):
        current_team = _canonicalize_player_like_list(analysis.current_team)
        starting_xi = _canonicalize_player_like_list(analysis.starting_xi)
        bench = _canonicalize_player_like_list(analysis.bench)
        player_positions = _canonicalize_player_positions(analysis.player_positions)
        transfers_in = _canonicalize_player_like_list(analysis.transfers_in)
        transfers_out = _canonicalize_player_like_list(analysis.transfers_out)
        captain = canonical_player_display(analysis.captain) if analysis.captain else None
        vice_captain = canonical_player_display(analysis.vice_captain) if analysis.vice_captain else None

        if not any(
            [
                current_team,
                starting_xi,
                bench,
                transfers_in,
                transfers_out,
                captain,
                vice_captain,
            ]
        ):
            continue

        confidence = (
            _confidence_score(analysis.team_reveal_confidence)
            if analysis.team_reveal_confidence is not None
            else _confidence_score(analysis.confidence)
        )
        reveals.append(
            ExpertTeamRevealItem(
                expert_name=analysis.expert_name,
                video_title=analysis.video_title,
                current_team=current_team,
                starting_xi=starting_xi,
                bench=bench,
                player_positions=player_positions,
                captain=captain,
                vice_captain=vice_captain,
                transfers_in=transfers_in,
                transfers_out=transfers_out,
                confidence=round(confidence, 4),
            )
        )

    return reveals


def dedupe_analyses(
    analyses: list[ExpertVideoAnalysis],
) -> tuple[list[ExpertVideoAnalysis], list[dict[str, str]]]:
    deduped: list[ExpertVideoAnalysis] = []
    seen: dict[str, ExpertVideoAnalysis] = {}
    duplicate_decisions: list[dict[str, str]] = []

    for analysis in analyses:
        identity, reason = build_analysis_identity(analysis)
        if identity in seen:
            duplicate_decisions.append(
                {
                    "kept_source": seen[identity].video_title,
                    "duplicate_source": analysis.video_title,
                    "kept_expert": seen[identity].expert_name,
                    "duplicate_expert": analysis.expert_name,
                    "reason": reason,
                }
            )
            continue
        seen[identity] = analysis
        deduped.append(analysis)

    return deduped, duplicate_decisions


def aggregate_player_consensus(
    analyses: list[ExpertVideoAnalysis],
) -> list[ConsensusItem]:
    grouped: dict[str, dict[str, object]] = {}

    for analysis in analyses:
        confidence = _confidence_score(analysis.confidence)
        for player_key in _unique_normalized_players(analysis.recommended_players):
            entry = grouped.setdefault(
                player_key,
                {"experts": set(), "confidences": []},
            )
            experts = entry["experts"]
            if analysis.expert_name in experts:
                continue
            experts.add(analysis.expert_name)
            entry["confidences"].append(confidence)

    items = [
        ConsensusItem(
            item=canonical_player_display(player_key),
            mention_count=len(data["experts"]),  # type: ignore[arg-type,index]
            average_confidence=round(
                sum(data["confidences"]) / len(data["confidences"]),  # type: ignore[arg-type,index]
                4,
            ),
            supporting_experts=_sorted_experts(data["experts"]),  # type: ignore[arg-type,index]
        )
        for player_key, data in grouped.items()
    ]
    return sorted(
        items,
        key=lambda item: (-item.mention_count, -item.average_confidence, normalize_lookup_key(item.item)),
    )


def aggregate_captaincy(
    analyses: list[ExpertVideoAnalysis],
) -> list[ConsensusItem]:
    grouped: dict[str, dict[str, object]] = {}

    for analysis in analyses:
        confidence = _confidence_score(analysis.confidence)
        for player_key in _unique_normalized_players(analysis.captaincy_picks):
            entry = grouped.setdefault(
                player_key,
                {"experts": set(), "confidences": []},
            )
            experts = entry["experts"]
            if analysis.expert_name in experts:
                continue
            experts.add(analysis.expert_name)
            entry["confidences"].append(confidence)

    items = [
        ConsensusItem(
            item=canonical_player_display(player_key),
            mention_count=len(data["experts"]),  # type: ignore[arg-type,index]
            average_confidence=round(
                sum(data["confidences"]) / len(data["confidences"]),  # type: ignore[arg-type,index]
                4,
            ),
            supporting_experts=_sorted_experts(data["experts"]),  # type: ignore[arg-type,index]
        )
        for player_key, data in grouped.items()
    ]
    return sorted(
        items,
        key=lambda item: (-item.mention_count, -item.average_confidence, normalize_lookup_key(item.item)),
    )


def aggregate_transfers(
    analyses: list[ExpertVideoAnalysis],
) -> list[TransferConsensusItem]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}

    for analysis in analyses:
        confidence = _confidence_score(analysis.confidence)

        for player_key in _unique_normalized_players(analysis.recommended_players):
            entry = grouped.setdefault(
                ("buy", player_key),
                {"experts": set(), "confidences": []},
            )
            experts = entry["experts"]
            if analysis.expert_name in experts:
                continue
            experts.add(analysis.expert_name)
            entry["confidences"].append(confidence)

        for player_key in _unique_normalized_players(analysis.avoid_players):
            entry = grouped.setdefault(
                ("sell", player_key),
                {"experts": set(), "confidences": []},
            )
            experts = entry["experts"]
            if analysis.expert_name in experts:
                continue
            experts.add(analysis.expert_name)
            entry["confidences"].append(confidence)

    items = [
        TransferConsensusItem(
            player_name=canonical_player_display(player_key),
            direction=direction,
            mention_count=len(data["experts"]),  # type: ignore[arg-type,index]
            average_confidence=round(
                sum(data["confidences"]) / len(data["confidences"]),  # type: ignore[arg-type,index]
                4,
            ),
            supporting_experts=_sorted_experts(data["experts"]),  # type: ignore[arg-type,index]
        )
        for (direction, player_key), data in grouped.items()
    ]
    return sorted(
        items,
        key=lambda item: (
            item.direction,
            -item.mention_count,
            -item.average_confidence,
            normalize_lookup_key(item.player_name),
        ),
    )


def aggregate_fixture_insights(
    analyses: list[ExpertVideoAnalysis],
) -> list[FixtureInsightConsensusItem]:
    grouped: dict[str, dict[str, object]] = {}

    for analysis in analyses:
        for raw_insight in analysis.key_takeaways + analysis.reasoning:
            insight_key = normalize_text_label(raw_insight)
            if not insight_key:
                continue

            entry = grouped.setdefault(
                insight_key,
                {"display": raw_insight.strip(), "experts": set()},
            )
            entry["experts"].add(analysis.expert_name)

    items = [
        FixtureInsightConsensusItem(
            insight=data["display"],  # type: ignore[index]
            mention_count=len(data["experts"]),  # type: ignore[arg-type,index]
            supporting_experts=_sorted_experts(data["experts"]),  # type: ignore[arg-type,index]
        )
        for data in grouped.values()
    ]
    return sorted(
        items,
        key=lambda item: (-item.mention_count, normalize_lookup_key(item.insight)),
    )


def aggregate_chip_strategy(
    analyses: list[ExpertVideoAnalysis],
) -> list[ConsensusItem]:
    grouped: dict[str, dict[str, object]] = {}

    for analysis in analyses:
        chip_key = normalize_chip_name(analysis.chip_strategy)
        if chip_key == "none":
            continue

        entry = grouped.setdefault(
            chip_key,
            {"experts": set(), "confidences": []},
        )
        experts = entry["experts"]
        if analysis.expert_name in experts:
            continue
        experts.add(analysis.expert_name)
        entry["confidences"].append(_confidence_score(analysis.confidence))

    items = [
        ConsensusItem(
            item=canonical_chip_display(chip_key),
            mention_count=len(data["experts"]),  # type: ignore[arg-type,index]
            average_confidence=round(
                sum(data["confidences"]) / len(data["confidences"]),  # type: ignore[arg-type,index]
                4,
            ),
            supporting_experts=_sorted_experts(data["experts"]),  # type: ignore[arg-type,index]
        )
        for chip_key, data in grouped.items()
    ]
    return sorted(
        items,
        key=lambda item: (-item.mention_count, -item.average_confidence, normalize_lookup_key(item.item)),
    )


def build_aggregated_fpl_report(
    analyses: list[ExpertVideoAnalysis],
) -> AggregatedFPLReport:
    deduped_analyses, _ = dedupe_analyses(analyses)
    analyses = deduped_analyses

    if not analyses:
        return AggregatedFPLReport(
            gameweek=None,
            expert_count=0,
            player_consensus=[],
            captaincy_consensus=[],
            transfer_consensus=[],
            fixture_insights=[],
            chip_strategy_consensus=[],
            disagreements=build_disagreement_report([]),
            conditional_advice=[],
            wait_for_news=[],
            expert_team_reveals=[],
        )

    conditional_advice = extract_conditional_advice(analyses)

    return AggregatedFPLReport(
        gameweek=analyses[0].gameweek,
        expert_count=len({analysis.expert_name for analysis in analyses}),
        player_consensus=aggregate_player_consensus(analyses),
        captaincy_consensus=aggregate_captaincy(analyses),
        transfer_consensus=aggregate_transfers(analyses),
        fixture_insights=aggregate_fixture_insights(analyses),
        chip_strategy_consensus=aggregate_chip_strategy(analyses),
        disagreements=build_disagreement_report(analyses),
        conditional_advice=conditional_advice,
        wait_for_news=extract_wait_for_news_entities(conditional_advice),
        expert_team_reveals=aggregate_expert_team_reveals(analyses),
    )
