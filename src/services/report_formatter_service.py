from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.services.normalization import (
    canonical_player_display,
    normalize_lookup_key,
    normalize_player_name,
    titleize_normalized,
)


@dataclass(frozen=True, slots=True)
class RankedInsight:
    title: str
    mention_count: int = 0
    average_confidence: float | None = None
    supporting_experts: tuple[str, ...] = ()


_PLAYER_PATTERNS: tuple[tuple[str, str], ...] = (
    ("bruno fernandes", "Bruno Fernandes"),
    ("erling haaland", "Erling Haaland"),
    ("alexander isak", "Alexander Isak"),
    ("jarrod bowen", "Jarrod Bowen"),
    ("antoine semenyo", "Antoine Semenyo"),
    ("mohamed salah", "Mohamed Salah"),
    ("bukayo saka", "Bukayo Saka"),
    ("cole palmer", "Cole Palmer"),
    ("ollie watkins", "Ollie Watkins"),
)


def _extract_canonical_player(text: str) -> str | None:
    normalized = normalize_lookup_key(text)
    for player_key, display_name in _PLAYER_PATTERNS:
        if player_key in normalized:
            return display_name

    for token_count in range(3, 0, -1):
        words = normalized.split()
        for index in range(0, max(len(words) - token_count + 1, 0)):
            candidate = " ".join(words[index : index + token_count])
            resolved = normalize_player_name(candidate)
            if resolved and resolved != candidate:
                return canonical_player_display(candidate)
    return None


def _normalize_recommendation_title(title: str) -> str:
    canonical_player = _extract_canonical_player(title)
    if canonical_player:
        return canonical_player
    return titleize_normalized(normalize_lookup_key(title)) or title.strip()


def _merge_ranked_insights(items: list[RankedInsight]) -> list[RankedInsight]:
    merged: OrderedDict[str, dict[str, object]] = OrderedDict()
    for item in items:
        key = normalize_lookup_key(item.title)
        bucket = merged.setdefault(
            key,
            {
                "title": item.title,
                "mention_count": 0,
                "confidence_weighted_total": 0.0,
                "confidence_mentions": 0,
                "supporting_experts": set(),
            },
        )
        bucket["mention_count"] = int(bucket["mention_count"]) + item.mention_count
        if item.average_confidence is not None and item.mention_count > 0:
            bucket["confidence_weighted_total"] = float(bucket["confidence_weighted_total"]) + (
                item.average_confidence * item.mention_count
            )
            bucket["confidence_mentions"] = int(bucket["confidence_mentions"]) + item.mention_count
        bucket["supporting_experts"] = set(bucket["supporting_experts"]) | set(item.supporting_experts)

    ranked = [
        RankedInsight(
            title=str(payload["title"]),
            mention_count=int(payload["mention_count"]),
            average_confidence=(
                None
                if int(payload["confidence_mentions"]) == 0
                else float(payload["confidence_weighted_total"]) / int(payload["confidence_mentions"])
            ),
            supporting_experts=tuple(sorted(set(payload["supporting_experts"]))),
        )
        for payload in merged.values()
    ]
    return sorted(
        ranked,
        key=lambda item: (
            -item.mention_count,
            -(item.average_confidence or 0.0),
            item.title,
        ),
    )


def rank_captaincy_insights(
    aggregate_report: AggregatedFPLReport,
    final_report: FinalGameweekReport,
    *,
    limit: int = 3,
) -> list[RankedInsight]:
    aggregate_items = [
        RankedInsight(
            title=_normalize_recommendation_title(item.item),
            mention_count=item.mention_count,
            average_confidence=item.average_confidence,
            supporting_experts=tuple(item.supporting_experts),
        )
        for item in aggregate_report.captaincy_consensus
    ]
    if aggregate_items:
        return _merge_ranked_insights(aggregate_items)[:limit]

    fallback_items = [
        RankedInsight(
            title=_normalize_recommendation_title(item.title),
            mention_count=1,
            average_confidence=item.confidence,
        )
        for item in final_report.captaincy
    ]
    return _merge_ranked_insights(fallback_items)[:limit]


def rank_transfer_insights(
    aggregate_report: AggregatedFPLReport,
    final_report: FinalGameweekReport,
    *,
    limit: int = 5,
) -> list[RankedInsight]:
    aggregate_items = [
        RankedInsight(
            title=f"{item.direction.title()} {canonical_player_display(item.player_name)}".strip(),
            mention_count=item.mention_count,
            average_confidence=item.average_confidence,
            supporting_experts=tuple(item.supporting_experts),
        )
        for item in aggregate_report.transfer_consensus
    ]
    if aggregate_items:
        return _merge_ranked_insights(aggregate_items)[:limit]

    fallback_items = [
        RankedInsight(
            title=titleize_normalized(normalize_lookup_key(item.title)) or item.title.strip(),
            mention_count=1,
            average_confidence=item.confidence,
        )
        for item in final_report.transfers
    ]
    return _merge_ranked_insights(fallback_items)[:limit]


def rank_chip_strategy_insights(
    aggregate_report: AggregatedFPLReport,
    final_report: FinalGameweekReport,
    *,
    limit: int = 3,
) -> list[RankedInsight]:
    aggregate_items = [
        RankedInsight(
            title=titleize_normalized(normalize_lookup_key(item.item)) or item.item.strip(),
            mention_count=item.mention_count,
            average_confidence=item.average_confidence,
            supporting_experts=tuple(item.supporting_experts),
        )
        for item in aggregate_report.chip_strategy_consensus
    ]
    if aggregate_items:
        return _merge_ranked_insights(aggregate_items)[:limit]

    fallback_items = [
        RankedInsight(
            title=titleize_normalized(normalize_lookup_key(item.title)) or item.title.strip(),
            mention_count=1,
            average_confidence=item.confidence,
        )
        for item in final_report.chip_strategy
    ]
    return _merge_ranked_insights(fallback_items)[:limit]


def _render_ranked_lines(items: list[RankedInsight]) -> list[str]:
    return [
        f"{index}. {item.title} (supported by {item.mention_count} expert"
        f"{'s' if item.mention_count != 1 else ''})"
        for index, item in enumerate(items, start=1)
    ]


def _render_ranked_bullets(items: list[RankedInsight]) -> list[str]:
    return [
        f"- {item.title} (supported by {item.mention_count} expert"
        f"{'s' if item.mention_count != 1 else ''})"
        for item in items
    ]


def _render_bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def format_gameweek_markdown_report(
    aggregate_report: AggregatedFPLReport,
    final_report: FinalGameweekReport,
) -> str:
    title = f"## GW{final_report.gameweek or aggregate_report.gameweek or '?'} FPL Expert Summary"
    lines = [title, "", final_report.overview]

    captaincy = rank_captaincy_insights(aggregate_report, final_report)
    if captaincy:
        lines.extend(["", "### Captaincy", *_render_ranked_lines(captaincy)])

    transfers = rank_transfer_insights(aggregate_report, final_report)
    if transfers:
        lines.extend(["", "### Transfers", *_render_ranked_bullets(transfers)])

    chip_strategy = rank_chip_strategy_insights(aggregate_report, final_report)
    if chip_strategy:
        lines.extend(["", "### Chip Strategy", *_render_ranked_bullets(chip_strategy)])

    risks = list(final_report.wait_for_news) + list(final_report.conditional_advice)
    if risks:
        lines.extend(["", "### Risks", *_render_bullet_lines(risks[:5])])

    fixture_notes = list(final_report.fixture_notes)
    if fixture_notes:
        lines.extend(["", "### Fixture Notes", *_render_bullet_lines(fixture_notes[:5])])

    if final_report.disagreements:
        lines.extend(
            [
                "",
                "### Disagreements",
                *[
                    f"- {item.topic}: {item.summary}"
                    for item in final_report.disagreements[:5]
                ],
            ]
        )

    if final_report.expert_team_reveals:
        lines.extend(
            [
                "",
                "### Expert Team Reveals",
                *[
                    f"- {item.expert_name}: {item.summary}"
                    for item in final_report.expert_team_reveals[:5]
                ],
            ]
        )

    lines.extend(["", "### Conclusion", final_report.conclusion])
    return "\n".join(lines).strip() + "\n"
