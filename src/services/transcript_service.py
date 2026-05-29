from __future__ import annotations

import random
import time
from pathlib import Path

from src.adapters.storage import load_transcript, save_transcript
from src.adapters.transcript_api import (
    TranscriptFetchError,
    WebshareProxySettings,
    fetch_transcript,
)
from src.app.core.config import settings
from src.utils.retry import RetryConfig, RetryError, retry_call
from src.utils.text_cleaning import clean_transcript

DEFAULT_TRANSCRIPT_CACHE_DIR = Path(settings.DATA_DIR) / "transcripts"


def _build_transcript_cache_path(video_id: str, cache_dir: str | Path) -> Path:
    return Path(cache_dir) / f"{video_id}.json"


def _load_cached_transcript(video_id: str, cache_dir: str | Path) -> dict | None:
    cache_path = _build_transcript_cache_path(video_id, cache_dir)
    if not cache_path.exists():
        return None

    payload = load_transcript(str(cache_path))
    if payload.get("status") != "available":
        return None
    if not isinstance(payload.get("transcript"), str) or not payload["transcript"].strip():
        return None
    return payload


def _save_cached_transcript(video_id: str, payload: dict, cache_dir: str | Path) -> None:
    save_transcript(
        str(_build_transcript_cache_path(video_id, cache_dir)),
        payload,
    )


def _sleep_before_transcript_fetch() -> None:
    time.sleep(random.uniform(1.0, 3.0))


def get_clean_transcript(
    video_id: str,
    *,
    proxy_settings: WebshareProxySettings | None = None,
    cache_dir: str | Path = DEFAULT_TRANSCRIPT_CACHE_DIR,
) -> dict:
    cached_payload = _load_cached_transcript(video_id, cache_dir)
    if cached_payload is not None:
        return cached_payload

    try:
        raw_text = retry_call(
            lambda: _fetch_transcript_with_delay(
                video_id,
                proxy_settings=proxy_settings,
            ),
            retry_on=(TranscriptFetchError,),
            context=f"Transcript fetch for video '{video_id}'",
            config=RetryConfig(max_attempts=3, initial_delay_seconds=0.1),
        )
    except RetryError as exc:
        return {
            "video_id": video_id,
            "transcript": "",
            "status": "error",
            "error": str(exc),
        }

    if not raw_text:
        return {
            "video_id": video_id,
            "transcript": "",
            "status": "missing",
        }

    cleaned = clean_transcript(raw_text)
    payload = {
        "video_id": video_id,
        "transcript": cleaned,
        "status": "available",
    }
    _save_cached_transcript(video_id, payload, cache_dir)
    return payload


def _fetch_transcript_with_delay(
    video_id: str,
    *,
    proxy_settings: WebshareProxySettings | None = None,
) -> str:
    _sleep_before_transcript_fetch()
    return fetch_transcript(video_id, proxy_settings=proxy_settings)
