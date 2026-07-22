from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from src.adapters.transcript_api import TranscriptFetchError
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.video_job import VideoAnalysisJob
from src.services.pipeline_service import run_pipeline
from src.services.transcript_service import get_clean_transcript
from src.services.transcript_ingestion_service import YouTubeIngestionResult


def _build_job(expert_name: str, *, url: str, transcript: str = "Useful transcript body") -> VideoAnalysisJob:
    return VideoAnalysisJob(
        expert_name=expert_name,
        video_title=f"{expert_name} GW32",
        published_at="2026-04-09T12:00:00Z",
        gameweek=32,
        transcript=transcript,
        video_url=url,
    )


def _build_analysis(job: VideoAnalysisJob) -> ExpertVideoAnalysis:
    return ExpertVideoAnalysis(
        expert_name=job.expert_name,
        video_title=job.video_title,
        gameweek=job.gameweek,
        summary="Summary",
        key_takeaways=[],
        recommended_players=["Saka"],
        avoid_players=[],
        captaincy_picks=[],
        chip_strategy=None,
        reasoning=[],
        confidence="medium",
    )


def test_get_clean_transcript_returns_readable_error_after_retries(monkeypatch) -> None:
    attempts = {"count": 0}

    def _fail(video_id: str, proxy_settings=None) -> str:
        attempts["count"] += 1
        raise TranscriptFetchError(f"temporary issue for {video_id}")

    monkeypatch.setattr("src.services.transcript_service.fetch_transcript", _fail)

    payload = get_clean_transcript("broken-video")

    assert payload["status"] == "error"
    assert "broken-video" in payload["error"]
    assert attempts["count"] == 3


def test_run_pipeline_skips_duplicate_jobs_and_preserves_partial_failures(tmp_path) -> None:
    jobs = [
        _build_job("Expert A", url="https://youtube.com/watch?v=dup123"),
        _build_job("Expert A Mirror", url="https://youtu.be/dup123"),
        _build_job("Expert B", url="https://youtube.com/watch?v=unique456"),
    ]
    output_dir = tmp_path / "runs" / "gw32"
    ingestion = YouTubeIngestionResult(
        configured_experts=5,
        discovered_videos=[
            {
                "video_id": f"video-{index}",
                "title": job.video_title,
                "video_url": job.video_url or "",
                "published_at": job.published_at,
                "expert_name": job.expert_name,
            }
            for index, job in enumerate(jobs, start=1)
        ],
        input_jobs=jobs,
        transcript_failures=[{"expert_name": "Expert C", "error": "missing"}],
    )

    async def fake_orchestration(queued_jobs: list[VideoAnalysisJob]):
        assert len(queued_jobs) == 2

        class _Result:
            def __init__(self) -> None:
                self.results = [
                    type(
                        "RunResult",
                        (),
                        {"success": True, "analysis": _build_analysis(queued_jobs[0]), "job": queued_jobs[0], "error": None},
                    )(),
                    type(
                        "RunResult",
                        (),
                        {"success": False, "analysis": None, "job": queued_jobs[1], "error": "provider timeout"},
                    )(),
                ]

        return _Result()

    with patch(
        "src.services.pipeline_service.ingest_youtube_video_jobs",
        return_value=ingestion,
    ), patch("src.services.pipeline_service.run_gameweek_orchestration", side_effect=fake_orchestration):
        result = asyncio.run(
            run_pipeline(
                season="2025-26",
                gameweek=32,
                output_dir=output_dir,
                synthesis_enabled=False,
            )
        )

    assert len(result.input_jobs) == 3
    assert len(result.expert_outputs) == 1
    assert len(result.failed_jobs) == 1
    assert result.duplicate_sources
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["duplicate_sources"] == 1
    assert manifest["counts"]["failed_jobs"] == 1
    assert manifest["counts"]["transcript_failures"] == 1
