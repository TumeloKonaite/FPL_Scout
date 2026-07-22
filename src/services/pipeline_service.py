from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from src.adapters.transcript_api import WebshareProxySettings
from src.orchestrators.gameweek_orchestrator import run_gameweek_orchestration
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.schemas.report_identity import ReportIdentity
from src.schemas.video_job import VideoAnalysisJob
from src.services.aggregation_service import (
    build_aggregated_fpl_report,
    dedupe_analyses,
)
from src.services.normalization import build_video_job_identity
from src.services.report_service import ReportService
from src.services.synthesis_service import (
    build_fallback_final_report,
    synthesize_final_report,
)
from src.services.transcript_ingestion_service import (
    YouTubeIngestionResult,
    ingest_youtube_video_jobs,
)


class PipelineServiceError(Exception):
    """Raised when the gameweek pipeline cannot complete successfully."""


@dataclass(slots=True)
class PipelineRunResult:
    run_path: Path
    season: str
    gameweek: int
    discovered_videos: list[dict[str, str]]
    input_jobs: list[VideoAnalysisJob]
    expert_outputs: list[ExpertVideoAnalysis]
    aggregate_report: AggregatedFPLReport
    final_report: FinalGameweekReport
    failed_jobs: list[tuple[VideoAnalysisJob, str]]
    synthesis_enabled: bool = True
    duplicate_sources: list[dict[str, str]] = field(default_factory=list)
    transcript_failures: list[dict[str, str]] = field(default_factory=list)
    configured_experts: int = 0


def dedupe_video_jobs(
    jobs: list[VideoAnalysisJob],
) -> tuple[list[VideoAnalysisJob], list[dict[str, str]]]:
    deduped: list[VideoAnalysisJob] = []
    kept_jobs: dict[str, VideoAnalysisJob] = {}
    duplicate_sources: list[dict[str, str]] = []

    for ordinal, job in enumerate(jobs, start=1):
        identity, reason = build_video_job_identity(job)
        label = job.video_url or f"{job.expert_name}::{job.video_title}"
        if identity in kept_jobs:
            original = kept_jobs[identity]
            duplicate_sources.append(
                {
                    "reason": reason,
                    "kept_expert": original.expert_name,
                    "kept_source": original.video_url
                    or f"{original.expert_name}::{original.video_title}",
                    "duplicate_expert": job.expert_name,
                    "duplicate_source": label,
                    "input_order": str(ordinal),
                }
            )
            continue
        kept_jobs[identity] = job
        deduped.append(job)

    return deduped, duplicate_sources


async def run_pipeline(
    *,
    season: str,
    gameweek: int,
    output_dir: str | Path,
    per_expert_limit: int = 2,
    archive_limit: int = 200,
    gameweek_deadline: str | None = None,
    expert_name: str | None = None,
    expert_count: int | None = None,
    synthesis_enabled: bool = True,
    report_service: ReportService | None = None,
    proxy_settings: WebshareProxySettings | None = None,
) -> PipelineRunResult:
    identity = ReportIdentity(season, gameweek)
    season = identity.season
    gameweek = identity.gameweek
    ingestion: YouTubeIngestionResult = ingest_youtube_video_jobs(
        gameweek=gameweek,
        season=season,
        gameweek_deadline=gameweek_deadline,
        per_expert_limit=per_expert_limit,
        archive_limit=archive_limit,
        expert_name=expert_name,
        expert_count=expert_count,
        proxy_settings=proxy_settings,
    )
    loaded_jobs = ingestion.input_jobs
    if not loaded_jobs:
        failure_details = "; ".join(
            f"{item.get('expert_name', 'Unknown expert')}: {item.get('error', 'unknown transcript failure')}"
            for item in ingestion.transcript_failures
        )
        raise PipelineServiceError(
            "Pipeline could not create any usable video analysis jobs from YouTube sources."
            + (f" Transcript failures: {failure_details}." if failure_details else "")
        )

    jobs, duplicate_sources = dedupe_video_jobs(loaded_jobs)
    orchestration = await run_gameweek_orchestration(jobs)

    raw_expert_outputs = [
        result.analysis
        for result in orchestration.results
        if result.success and result.analysis is not None
    ]
    expert_outputs, analysis_duplicates = dedupe_analyses(raw_expert_outputs)
    for decision in analysis_duplicates:
        duplicate_sources.append({**decision, "input_order": "analysis"})
    failed_jobs = [
        (result.job, result.error or "Unknown pipeline error")
        for result in orchestration.results
        if not result.success
    ]

    if not expert_outputs:
        failure_details = "; ".join(
            f"{job.expert_name}: {error}" for job, error in failed_jobs
        )
        raise PipelineServiceError(
            "Pipeline did not produce any expert analyses."
            + (f" Failures: {failure_details}." if failure_details else "")
        )

    aggregate_report = build_aggregated_fpl_report(
        expert_outputs, season=season, gameweek=gameweek
    )
    final_report = (
        await synthesize_final_report(aggregate_report)
        if synthesis_enabled
        else build_fallback_final_report(aggregate_report)
    )

    run_path = (report_service or ReportService()).persist_run(
        discovered_videos=ingestion.discovered_videos,
        input_jobs=loaded_jobs,
        expert_outputs=expert_outputs,
        aggregate_report=aggregate_report,
        final_report=final_report,
        failed_jobs=[
            {
                "expert_name": job.expert_name,
                "video_title": job.video_title,
                "error": error,
            }
            for job, error in failed_jobs
        ],
        duplicate_sources=duplicate_sources,
        input_mode="youtube_auto",
        configured_experts=ingestion.configured_experts,
        videos_discovered=ingestion.videos_discovered,
        videos_selected=ingestion.videos_selected,
        jobs_created=len(loaded_jobs),
        transcript_failures=ingestion.transcript_failures,
        run_dir=output_dir,
    )

    return PipelineRunResult(
        run_path=run_path,
        season=season,
        gameweek=gameweek,
        discovered_videos=ingestion.discovered_videos,
        input_jobs=loaded_jobs,
        expert_outputs=expert_outputs,
        aggregate_report=aggregate_report,
        final_report=final_report,
        failed_jobs=failed_jobs,
        duplicate_sources=duplicate_sources,
        synthesis_enabled=synthesis_enabled,
        transcript_failures=ingestion.transcript_failures,
        configured_experts=ingestion.configured_experts,
    )


def run_pipeline_sync(
    *,
    season: str,
    gameweek: int,
    output_dir: str | Path,
    per_expert_limit: int = 2,
    archive_limit: int = 200,
    gameweek_deadline: str | None = None,
    expert_name: str | None = None,
    expert_count: int | None = None,
    synthesis_enabled: bool = True,
    report_service: ReportService | None = None,
    proxy_settings: WebshareProxySettings | None = None,
) -> PipelineRunResult:
    return asyncio.run(
        run_pipeline(
            season=season,
            gameweek=gameweek,
            output_dir=output_dir,
            per_expert_limit=per_expert_limit,
            archive_limit=archive_limit,
            gameweek_deadline=gameweek_deadline,
            expert_name=expert_name,
            expert_count=expert_count,
            synthesis_enabled=synthesis_enabled,
            report_service=report_service,
            proxy_settings=proxy_settings,
        )
    )
