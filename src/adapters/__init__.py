"""Adapter interfaces for transcript ingestion and persistence."""

from src.adapters.storage import load_transcript, save_transcript
from src.adapters.transcript_api import fetch_transcript
from src.adapters.youtube import (
    fetch_youtube_transcript,
    get_latest_videos_for_all_experts,
    get_latest_videos_for_expert,
    get_videos_for_gameweek,
)

__all__ = [
    "fetch_transcript",
    "fetch_youtube_transcript",
    "get_latest_videos_for_expert",
    "get_latest_videos_for_all_experts",
    "get_videos_for_gameweek",
    "load_transcript",
    "save_transcript",
]
