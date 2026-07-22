from __future__ import annotations

from dataclasses import dataclass
import inspect

from src.adapters.transcript_api import WebshareProxySettings
from src.adapters.youtube import get_latest_videos_for_expert
from src.config.expert_sources import EXPERT_CHANNELS
from src.schemas.video_job import VideoAnalysisJob
from src.services.transcript_service import get_clean_transcript
from src.services.video_selection_service import filter_relevant_videos


@dataclass(slots=True)
class YouTubeIngestionResult:
    configured_experts: int
    discovered_videos: list[dict[str, str]]
    input_jobs: list[VideoAnalysisJob]
    transcript_failures: list[dict[str, str]]

    @property
    def videos_discovered(self) -> int:
        return len(self.discovered_videos)

    @property
    def videos_selected(self) -> int:
        return len(self.input_jobs)

    @property
    def jobs_created(self) -> int:
        return len(self.input_jobs)


def _select_experts(
    *,
    expert_name: str | None = None,
    expert_count: int | None = None,
) -> list[dict[str, str]]:
    experts = [expert for expert in EXPERT_CHANNELS if isinstance(expert.get("name"), str) and isinstance(expert.get("url"), str)]

    if expert_name:
        requested = expert_name.strip().casefold()
        experts = [
            expert
            for expert in experts
            if str(expert.get("name", "")).strip().casefold() == requested
        ]

    if expert_count is not None:
        if expert_count <= 0:
            return []
        experts = experts[:expert_count]

    return experts


def ingest_youtube_video_jobs(
    *,
    gameweek: int,
    per_expert_limit: int = 2,
    expert_name: str | None = None,
    expert_count: int | None = None,
    proxy_settings: WebshareProxySettings | None = None,
) -> YouTubeIngestionResult:
    selected_experts = _select_experts(
        expert_name=expert_name,
        expert_count=expert_count,
    )
    discovered_videos: list[dict[str, str]] = []
    for expert in selected_experts:
        discovered_videos.extend(
            get_latest_videos_for_expert(
                expert_name=str(expert["name"]),
                channel_url=str(expert["url"]),
                limit=per_expert_limit,
            )
        )

    transcript_candidates: list[dict[str, str]] = []
    transcript_failures: list[dict[str, str]] = []
    for video in discovered_videos:
        video_id = video.get("video_id")
        if not isinstance(video_id, str) or not video_id:
            transcript_failures.append(
                {
                    "expert_name": str(video.get("expert_name", "")),
                    "video_title": str(video.get("title", "")),
                    "video_url": str(video.get("video_url", "")),
                    "video_id": "",
                    "error": "missing video id",
                    "status": "invalid",
                }
            )
            continue

        transcript_kwargs = {"proxy_settings": proxy_settings}
        # Preserve compatibility with injected legacy fetch callables while
        # passing provenance to the database-backed implementation.
        if "video_url" in inspect.signature(get_clean_transcript).parameters:
            transcript_kwargs.update(
                video_url=video.get("video_url"),
                title=video.get("title"),
                expert=video.get("expert_name"),
            )
        transcript_payload = get_clean_transcript(video_id, **transcript_kwargs)
        if transcript_payload.get("status") != "available":
            transcript_failures.append(
                {
                    "expert_name": str(video.get("expert_name", "")),
                    "video_title": str(video.get("title", "")),
                    "video_url": str(video.get("video_url", "")),
                    "video_id": video_id,
                    "error": str(transcript_payload.get("error", transcript_payload.get("status", "unavailable"))),
                    "status": str(transcript_payload.get("status", "unavailable")),
                }
            )
            continue

        transcript_text = transcript_payload.get("transcript", "")
        if not isinstance(transcript_text, str) or not transcript_text.strip():
            transcript_failures.append(
                {
                    "expert_name": str(video.get("expert_name", "")),
                    "video_title": str(video.get("title", "")),
                    "video_url": str(video.get("video_url", "")),
                    "video_id": video_id,
                    "error": "empty transcript",
                    "status": "empty",
                }
            )
            continue

        transcript_candidates.append(
            {
                **video,
                "transcript": transcript_text,
                "transcript_id": transcript_payload.get("transcript_id"),
                "transcript_revision_id": transcript_payload.get("transcript_revision_id"),
            }
        )

    relevant_videos = filter_relevant_videos(transcript_candidates, gameweek=gameweek)

    input_jobs = [
        VideoAnalysisJob(
            expert_name=video["expert_name"],
            video_title=video["title"],
            published_at=video["published_at"],
            gameweek=gameweek,
            transcript=video["transcript"],
            video_url=video.get("video_url"),
            transcript_id=video.get("transcript_id"),
            transcript_revision_id=video.get("transcript_revision_id"),
        )
        for video in relevant_videos
    ]

    return YouTubeIngestionResult(
        configured_experts=len(selected_experts),
        discovered_videos=discovered_videos,
        input_jobs=input_jobs,
        transcript_failures=transcript_failures,
    )


def build_video_jobs_from_youtube(
    *,
    gameweek: int,
    per_expert_limit: int = 2,
    expert_name: str | None = None,
    expert_count: int | None = None,
    proxy_settings: WebshareProxySettings | None = None,
) -> list[VideoAnalysisJob]:
    return ingest_youtube_video_jobs(
        gameweek=gameweek,
        per_expert_limit=per_expert_limit,
        expert_name=expert_name,
        expert_count=expert_count,
        proxy_settings=proxy_settings,
    ).input_jobs
