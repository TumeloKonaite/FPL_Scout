from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.app.domain.reports.player_catalogue import CataloguePlayer, PlayerCatalogue
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.video_job import VideoAnalysisJob
from src.services import pipeline_service


@pytest.mark.anyio
async def test_historical_pipeline_loads_matching_persisted_catalogue(
    monkeypatch,
) -> None:
    job = VideoAnalysisJob(
        expert_name="Alpha",
        video_title="GW31",
        published_at="2026-03-01T00:00:00Z",
        gameweek=31,
        transcript="Player One is in my team.",
        video_url="https://example.test/video",
    )
    analysis = ExpertVideoAnalysis(
        expert_name="Alpha",
        video_title="GW31",
        gameweek=31,
        summary="A partial reveal.",
        key_takeaways=[],
        recommended_players=[],
        avoid_players=[],
        captaincy_picks=[],
        reasoning=[],
        confidence="high",
        current_team=["Player One"],
        source_url=job.video_url,
    )
    ingestion = SimpleNamespace(
        input_jobs=[job],
        discovered_videos=[],
        transcript_failures=[],
        configured_experts=1,
        videos_discovered=1,
        videos_selected=1,
    )
    monkeypatch.setattr(
        pipeline_service, "ingest_youtube_video_jobs", lambda **kwargs: ingestion
    )

    async def orchestrate(jobs):
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    success=True,
                    analysis=analysis,
                    job=job,
                    error=None,
                )
            ]
        )

    monkeypatch.setattr(
        pipeline_service, "run_gameweek_orchestration", orchestrate
    )

    class Provider:
        def __init__(self) -> None:
            self.requests: list[str] = []

        def get_catalogue(self, season: str) -> PlayerCatalogue:
            self.requests.append(season)
            return PlayerCatalogue(
                [CataloguePlayer(1, "Player One", "MID")],
                season=season,
                source="persisted_snapshot",
                snapshot_id=f"{season}:test",
            )

    class Reports:
        def persist_run(self, **kwargs) -> str:
            team = kwargs["final_report"].suggested_team
            assert team.catalogueSeason == "2025-26"
            assert team.catalogueSnapshotIdentifier == "2025-26:test"
            return "run-31"

    provider = Provider()
    result = await pipeline_service.run_pipeline(
        season="2025-26",
        gameweek=31,
        gameweek_deadline="2026-03-14T13:30:00Z",
        synthesis_enabled=False,
        player_catalogue_provider=provider,
        report_service=Reports(),  # type: ignore[arg-type]
    )

    assert provider.requests == ["2025-26"]
    assert result.final_report.suggested_team is not None
    assert result.final_report.suggested_team.failureReason == (
        "insufficient_contributing_experts"
    )
