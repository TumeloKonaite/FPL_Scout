from __future__ import annotations

import asyncio
from typing import Sequence

from agents import Runner

from src.agents.model_factory import close_openai_model
from src.agents.expert_video_agent import build_expert_video_agent
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.video_job import VideoAnalysisJob


MIN_TRANSCRIPT_CHAR_LENGTH = 40


def get_analysis_agent():
    """Build an analysis agent with a client scoped to the current event loop."""
    return build_expert_video_agent()


def _build_analysis_prompt(job: VideoAnalysisJob) -> str:
    """Format the user prompt passed to the analysis agent."""
    transcript = job.transcript.strip()

    return f"""
Expert: {job.expert_name}
Video title: {job.video_title}
Gameweek: {job.gameweek}

Transcript:
{transcript}
""".strip()


def _is_transcript_too_short(transcript: str) -> bool:
    """Return True if transcript is empty or too short for meaningful analysis."""
    cleaned = transcript.strip()
    return not cleaned or len(cleaned) < MIN_TRANSCRIPT_CHAR_LENGTH


def _build_minimal_analysis(job: VideoAnalysisJob) -> ExpertVideoAnalysis:
    """Return a safe fallback structured output for empty or short transcripts."""
    return ExpertVideoAnalysis(
        expert_name=job.expert_name,
        video_title=job.video_title,
        gameweek=job.gameweek,
        summary="Transcript was empty or too short for reliable analysis.",
        key_takeaways=[],
        recommended_players=[],
        avoid_players=[],
        captaincy_picks=[],
        chip_strategy=None,
        reasoning=[],
        confidence="low",
        current_team=[],
        starting_xi=[],
        bench=[],
        captain=None,
        vice_captain=None,
        transfers_in=[],
        transfers_out=[],
        team_reveal_confidence=None,
    )


async def analyze_video_job(job: VideoAnalysisJob) -> ExpertVideoAnalysis:
    """Analyze a single video transcript and return a structured ExpertVideoAnalysis."""
    transcript = job.transcript.strip()

    if _is_transcript_too_short(transcript):
        return _build_minimal_analysis(job)

    prompt = _build_analysis_prompt(job)
    agent = get_analysis_agent()
    try:
        result = await Runner.run(agent, prompt)
    finally:
        await close_openai_model(agent.model)

    if not isinstance(result.final_output, ExpertVideoAnalysis):
        raise TypeError("Agent did not return ExpertVideoAnalysis")

    return result.final_output


async def analyze_video_jobs(
    jobs: Sequence[VideoAnalysisJob],
) -> list[ExpertVideoAnalysis]:
    """Analyze multiple video jobs concurrently."""
    if not jobs:
        return []

    tasks = [analyze_video_job(job) for job in jobs]
    results = await asyncio.gather(*tasks)
    return list(results)
