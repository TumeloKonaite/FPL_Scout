from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from src.schemas.aggregate_report import DisagreementReport
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.schemas.video_job import VideoAnalysisJob
from src.services.pipeline_service import PipelineServiceError, run_pipeline
from src.services.transcript_ingestion_service import YouTubeIngestionResult


def _build_job(*, expert_name: str = "Expert A", gameweek: int = 32) -> VideoAnalysisJob:
    return VideoAnalysisJob(
        expert_name=expert_name,
        video_title=f"{expert_name} GW{gameweek}",
        published_at="2026-04-09T12:00:00Z",
        gameweek=gameweek,
        transcript="Transcript",
        video_url=f"https://youtube.com/watch?v={expert_name.lower().replace(' ', '-')}",
    )


def _build_analysis(job: VideoAnalysisJob) -> ExpertVideoAnalysis:
    return ExpertVideoAnalysis(
        expert_name=job.expert_name,
        video_title=job.video_title,
        gameweek=job.gameweek,
        summary="Summary",
        key_takeaways=["Takeaway"],
        recommended_players=["Bukayo Saka"],
        avoid_players=[],
        captaincy_picks=["Mohamed Salah"],
        chip_strategy=None,
        reasoning=["Fixtures"],
        confidence="high",
    )


def _build_aggregate_report(gameweek: int = 32) -> AggregatedFPLReport:
    return AggregatedFPLReport(
        season="2025-26",
        gameweek=gameweek,
        expert_count=1,
        player_consensus=[],
        captaincy_consensus=[],
        transfer_consensus=[],
        fixture_insights=[],
        chip_strategy_consensus=[],
        disagreements=DisagreementReport(),
        conditional_advice=[],
        wait_for_news=[],
    )


def _build_final_report(gameweek: int = 32) -> FinalGameweekReport:
    return FinalGameweekReport(
        season="2025-26",
        gameweek=gameweek,
        overview="Overview",
        transfers=[],
        captaincy=[],
        chip_strategy=[],
        fixture_notes=[],
        disagreements=[],
        conditional_advice=[],
        wait_for_news=[],
        expert_team_reveals=[],
        conclusion="Conclusion",
    )


def test_run_pipeline_persists_artifacts_to_requested_output_dir(tmp_path) -> None:
    job = _build_job()
    analysis = _build_analysis(job)
    aggregate_report = _build_aggregate_report()
    final_report = _build_final_report()
    output_dir = tmp_path / "runs" / "gw32"
    ingestion = YouTubeIngestionResult(
        configured_experts=5,
        discovered_videos=[
            {
                "video_id": "expert-a",
                "title": job.video_title,
                "video_url": job.video_url or "",
                "published_at": job.published_at,
                "expert_name": job.expert_name,
            }
        ],
        input_jobs=[job],
        transcript_failures=[],
    )

    async def fake_orchestration(jobs: list[VideoAnalysisJob]):
        class _Result:
            def __init__(self) -> None:
                self.results = [
                    type(
                        "RunResult",
                        (),
                        {"success": True, "analysis": analysis, "job": jobs[0], "error": None},
                    )()
                ]

        return _Result()

    with patch(
        "src.services.pipeline_service.ingest_youtube_video_jobs",
        return_value=ingestion,
    ), patch(
        "src.services.pipeline_service.run_gameweek_orchestration",
        side_effect=fake_orchestration,
    ), patch(
        "src.services.pipeline_service.build_aggregated_fpl_report",
        return_value=aggregate_report,
    ), patch(
        "src.services.pipeline_service.synthesize_final_report",
        return_value=final_report,
    ):
        result = asyncio.run(
            run_pipeline(
                season="2025-26",
                gameweek=32,
                output_dir=output_dir,
            )
        )

    assert result.run_path == output_dir
    assert (output_dir / "discovered_videos.json").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "report.md").exists()
    assert json.loads((output_dir / "expert_outputs.json").read_text(encoding="utf-8")) == [
        analysis.model_dump()
    ]
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_mode"] == "youtube_auto"
    assert manifest["configured_experts"] == 5
    assert manifest["videos_discovered"] == 1
    assert manifest["videos_selected"] == 1
    assert manifest["jobs_created"] == 1
    assert result.duplicate_sources == []


def test_run_pipeline_uses_fallback_report_when_synthesis_is_disabled(tmp_path) -> None:
    job = _build_job()
    analysis = _build_analysis(job)
    aggregate_report = _build_aggregate_report()
    fallback_report = _build_final_report()
    output_dir = tmp_path / "runs" / "gw32"
    ingestion = YouTubeIngestionResult(
        configured_experts=5,
        discovered_videos=[
            {
                "video_id": "expert-a",
                "title": job.video_title,
                "video_url": job.video_url or "",
                "published_at": job.published_at,
                "expert_name": job.expert_name,
            }
        ],
        input_jobs=[job],
        transcript_failures=[],
    )

    async def fake_orchestration(jobs: list[VideoAnalysisJob]):
        class _Result:
            def __init__(self) -> None:
                self.results = [
                    type(
                        "RunResult",
                        (),
                        {"success": True, "analysis": analysis, "job": jobs[0], "error": None},
                    )()
                ]

        return _Result()

    with patch(
        "src.services.pipeline_service.ingest_youtube_video_jobs",
        return_value=ingestion,
    ), patch(
        "src.services.pipeline_service.run_gameweek_orchestration",
        side_effect=fake_orchestration,
    ), patch(
        "src.services.pipeline_service.build_aggregated_fpl_report",
        return_value=aggregate_report,
    ), patch(
        "src.services.pipeline_service.build_fallback_final_report",
        return_value=fallback_report,
    ) as mocked_fallback, patch(
        "src.services.pipeline_service.synthesize_final_report",
    ) as mocked_synthesis:
        result = asyncio.run(
            run_pipeline(
                season="2025-26",
                gameweek=32,
                output_dir=output_dir,
                synthesis_enabled=False,
            )
        )

    assert result.final_report == fallback_report
    mocked_fallback.assert_called_once_with(aggregate_report)
    mocked_synthesis.assert_not_called()


def test_run_pipeline_raises_readable_error_when_ingestion_builds_no_jobs(tmp_path) -> None:
    output_dir = tmp_path / "runs" / "gw32"
    ingestion = YouTubeIngestionResult(
        configured_experts=5,
        discovered_videos=[],
        input_jobs=[],
        transcript_failures=[{"expert_name": "Expert A", "error": "missing"}],
    )

    with patch(
        "src.services.pipeline_service.ingest_youtube_video_jobs",
        return_value=ingestion,
    ), pytest.raises(
        PipelineServiceError,
        match="Pipeline could not create any usable video analysis jobs from YouTube sources",
    ):
        asyncio.run(
            run_pipeline(
                season="2025-26",
                gameweek=32,
                output_dir=output_dir,
            )
        )
