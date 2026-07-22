from __future__ import annotations

from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport
from src.services.aggregation_service import build_aggregated_fpl_report


def _build_analysis(
    expert_name: str,
    *,
    recommended_players: list[str] | None = None,
    avoid_players: list[str] | None = None,
    captaincy_picks: list[str] | None = None,
    chip_strategy: str | None = None,
    key_takeaways: list[str] | None = None,
    reasoning: list[str] | None = None,
    confidence: str = "medium",
    current_team: list[str] | None = None,
    starting_xi: list[str] | None = None,
    bench: list[str] | None = None,
    player_positions: dict[str, str] | None = None,
    captain: str | None = None,
    vice_captain: str | None = None,
    transfers_in: list[str] | None = None,
    transfers_out: list[str] | None = None,
    team_reveal_confidence: str | None = None,
) -> ExpertVideoAnalysis:
    return ExpertVideoAnalysis(
        expert_name=expert_name,
        video_title=f"{expert_name} GW5",
        gameweek=5,
        summary=f"Summary for {expert_name}",
        key_takeaways=key_takeaways or [],
        recommended_players=recommended_players or [],
        avoid_players=avoid_players or [],
        captaincy_picks=captaincy_picks or [],
        chip_strategy=chip_strategy,
        reasoning=reasoning or [],
        confidence=confidence,
        current_team=current_team or [],
        starting_xi=starting_xi or [],
        bench=bench or [],
        player_positions=player_positions or {},
        captain=captain,
        vice_captain=vice_captain,
        transfers_in=transfers_in or [],
        transfers_out=transfers_out or [],
        team_reveal_confidence=team_reveal_confidence,
    )


def test_player_consensus_counts_supporting_experts_once() -> None:
    analyses = [
        _build_analysis("Expert A", recommended_players=["Saka", "Bukayo Saka"], confidence="high"),
        _build_analysis("Expert B", recommended_players=["Bukayo Saka"], confidence="medium"),
        _build_analysis("Expert C", recommended_players=["Salah"], confidence="low"),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    assert report.player_consensus[0].item == "Bukayo Saka"
    assert report.player_consensus[0].mention_count == 2
    assert report.player_consensus[0].supporting_experts == ["Expert A", "Expert B"]
    assert report.player_consensus[0].relevant_expert_count == 3
    assert report.player_consensus[0].support_ratio == 0.6667
    assert report.player_consensus[0].consensus == "moderate"
    assert report.player_consensus[0].opposition_count == 1


def test_source_mentions_do_not_inflate_unique_expert_support() -> None:
    first = _build_analysis("Expert A", captaincy_picks=["Salah"])
    first.published_at = "2026-07-19T10:00:00+00:00"
    first.source_url = "https://example.com/first"
    second = _build_analysis("Expert A", captaincy_picks=["Salah"])
    second.video_title = "Expert A deadline stream"
    second.summary = "A separate source"
    third = _build_analysis("Expert B", captaincy_picks=["Haaland"])

    report = build_aggregated_fpl_report([first, second, third], season="2025-26", gameweek=5)
    salah = next(item for item in report.captaincy_consensus if item.item == "Mohamed Salah")

    assert salah.mention_count == 1
    assert len([source for source in salah.sources if source.position == "support"]) == 2
    assert salah.sources[0].name == "Expert A"
    assert salah.sources[0].url == "https://example.com/first"
    assert salah.sources[0].publishedAt == "2026-07-19T10:00:00+00:00"
    assert salah.alternatives[0].recommendation == "Erling Haaland"
    assert salah.consensus == "split"


def test_confidence_averaging_is_arithmetic_mean() -> None:
    analyses = [
        _build_analysis("Expert A", recommended_players=["Salah"], confidence="high"),
        _build_analysis("Expert B", recommended_players=["Mohamed Salah"], confidence="medium"),
        _build_analysis("Expert C", recommended_players=["Salah"], confidence="low"),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    salah = report.player_consensus[0]
    assert salah.item == "Mohamed Salah"
    assert salah.mention_count == 3
    assert salah.average_confidence == 0.6667


def test_duplicate_mentions_are_normalized_consistently() -> None:
    analyses = [
        _build_analysis(
            "Expert A",
            recommended_players=["Saka", "Bukayo Saka", " SAKA "],
            captaincy_picks=["Haaland", "Erling Haaland"],
            chip_strategy="WC",
            confidence="high",
        ),
        _build_analysis(
            "Expert B",
            recommended_players=["Bukayo Saka"],
            captaincy_picks=["Erling Haaland"],
            chip_strategy="wildcard",
            confidence="medium",
        ),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    assert [item.item for item in report.player_consensus] == ["Bukayo Saka"]
    assert report.player_consensus[0].mention_count == 2
    assert [item.item for item in report.captaincy_consensus] == ["Erling Haaland"]
    assert report.captaincy_consensus[0].mention_count == 2
    assert [item.item for item in report.chip_strategy_consensus] == ["wildcard"]


def test_aggregated_report_is_schema_valid_for_empty_input() -> None:
    report = build_aggregated_fpl_report([], season="2025-26", gameweek=5)

    validated = AggregatedFPLReport.model_validate(report.model_dump())

    assert validated.expert_count == 0
    assert validated.gameweek == 5
    assert validated.player_consensus == []
    assert validated.transfer_consensus == []
    assert validated.fixture_insights == []
    assert validated.disagreements.players == []
    assert validated.conditional_advice == []
    assert validated.wait_for_news == []


def test_transfer_and_fixture_aggregation_are_deterministic() -> None:
    analyses = [
        _build_analysis(
            "Expert B",
            recommended_players=["Salah"],
            avoid_players=["Watkins"],
            key_takeaways=["Arsenal have a strong fixture run"],
            reasoning=["Arsenal have a strong fixture run"],
            confidence="medium",
        ),
        _build_analysis(
            "Expert A",
            recommended_players=["Mohamed Salah"],
            avoid_players=["Ollie Watkins"],
            key_takeaways=["Arsenal have a strong fixture run"],
            reasoning=["Liverpool attack still looks elite"],
            confidence="high",
        ),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    assert [item.player_name for item in report.transfer_consensus] == [
        "Mohamed Salah",
        "Ollie Watkins",
    ]
    assert [item.direction for item in report.transfer_consensus] == ["buy", "sell"]
    assert report.fixture_insights[0].insight == "Arsenal have a strong fixture run"
    assert report.fixture_insights[0].mention_count == 2


def test_transfer_opposition_is_attributed_without_becoming_support() -> None:
    report = build_aggregated_fpl_report(
        [
            _build_analysis("Expert A", recommended_players=["Saka"]),
            _build_analysis("Expert B", avoid_players=["Bukayo Saka"]),
        ],
        season="2025-26",
        gameweek=5,
    )

    buy = next(
        item
        for item in report.transfer_consensus
        if item.direction == "buy" and item.player_name == "Bukayo Saka"
    )
    assert buy.mention_count == 1
    assert buy.relevant_expert_count == 2
    assert buy.opposition_count == 1
    assert buy.consensus == "split"
    assert any(source.name == "Expert B" and source.position == "oppose" for source in buy.sources)


def test_aggregated_report_includes_disagreements_and_conditional_advice() -> None:
    analyses = [
        _build_analysis(
            "Expert A",
            recommended_players=["Saka"],
            captaincy_picks=["Salah"],
            reasoning=["Wait for press conference news on Saka", "I would roll the transfer"],
            confidence="high",
        ),
        _build_analysis(
            "Expert B",
            avoid_players=["Bukayo Saka"],
            captaincy_picks=["Haaland"],
            reasoning=["I would buy now before the deadline"],
            confidence="medium",
        ),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    assert report.disagreements.players[0].player == "Bukayo Saka"
    assert report.disagreements.captaincy[0].options == [
        "Erling Haaland",
        "Mohamed Salah",
    ]
    assert report.disagreements.captaincy[0].expert_map["Erling Haaland"] == ["Expert B"]
    assert report.disagreements.captaincy[0].expert_map["Mohamed Salah"] == ["Expert A"]
    assert report.disagreements.strategy[0].side_a == "roll"
    assert report.disagreements.strategy[0].side_b == "buy_now"
    assert report.conditional_advice[0].reason == "press_conference"
    assert report.wait_for_news == ["Bukayo Saka"]


def test_aggregated_report_includes_explicit_expert_team_reveals() -> None:
    analyses = [
        _build_analysis(
            "Expert A",
            current_team=["Saka", "Salah", "Bruno Fernandes"],
            starting_xi=["Saka", "Salah", "Bruno Fernandes"],
            bench=["Fabianski"],
            player_positions={
                "Saka": "MID",
                "Salah": "MID",
                "Fabianski": "GK",
            },
            captain="Salah",
            vice_captain="Saka",
            transfers_in=["Bruno Fernandes"],
            transfers_out=["Ollie Watkins"],
            team_reveal_confidence="high",
        ),
        _build_analysis("Expert B", recommended_players=["Haaland"]),
    ]

    report = build_aggregated_fpl_report(analyses, season="2025-26", gameweek=5)

    assert len(report.expert_team_reveals) == 1
    reveal = report.expert_team_reveals[0]
    assert reveal.expert_name == "Expert A"
    assert reveal.captain == "Mohamed Salah"
    assert reveal.vice_captain == "Bukayo Saka"
    assert reveal.player_positions == {
        "Bukayo Saka": "MID",
        "Mohamed Salah": "MID",
        "Fabianski": "GK",
    }
    assert reveal.transfers_in == ["Bruno Fernandes"]
    assert reveal.transfers_out == ["Ollie Watkins"]
