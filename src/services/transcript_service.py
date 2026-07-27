from __future__ import annotations

import random
import time
from pathlib import Path

from src.adapters.transcript_api import (
    TranscriptFetchError,
    WebshareProxySettings,
    fetch_transcript,
)
from src.app.infrastructure.models import Transcript, TranscriptStatus
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.utils.retry import RetryConfig, RetryError, retry_call
from src.utils.text_cleaning import clean_transcript


def _payload_from_record(record: Transcript, repository: TranscriptRepository) -> dict:
    revision = repository.get_current_revision(record.id)
    status = {
        TranscriptStatus.AVAILABLE: "available",
        TranscriptStatus.UNAVAILABLE: "missing",
        TranscriptStatus.FAILED: "error",
    }[record.status]
    payload = {
        "video_id": record.video_id,
        "transcript": record.transcript_text or "",
        "status": status,
        "transcript_id": str(record.id),
        "transcript_revision_id": str(revision.id) if revision else None,
    }
    if record.failure_reason:
        payload["error"] = record.failure_reason
    if record.failure_code:
        payload["failure_code"] = record.failure_code
    return payload


def get_clean_transcript(
    video_id: str,
    *,
    proxy_settings: WebshareProxySettings | None = None,
    cache_dir: str | Path | None = None,
    repository: TranscriptRepository | None = None,
    video_url: str | None = None,
    title: str | None = None,
    expert: str | None = None,
    source_language: str | None = None,
) -> dict:
    # cache_dir remains a no-op keyword for caller compatibility. PostgreSQL is
    # mandatory and database errors deliberately propagate to the caller.
    del cache_dir
    repo = repository or TranscriptRepository()
    record = repo.get_by_video_id(video_id)
    if record is not None and (
        record.status == TranscriptStatus.AVAILABLE or not repo.should_retry(record)
    ):
        return _payload_from_record(record, repo)

    try:
        raw_text = retry_call(
            lambda: _fetch_transcript_with_delay(
                video_id, proxy_settings=proxy_settings
            ),
            retry_on=(TranscriptFetchError,),
            context=f"Transcript fetch for video '{video_id}'",
            config=RetryConfig(max_attempts=3, initial_delay_seconds=0.1),
        )
    except RetryError as exc:
        saved = repo.save_failure(
            video_id=video_id,
            status=TranscriptStatus.FAILED,
            failure_code="youtube_fetch_failed",
            failure_reason=str(exc),
            video_url=video_url,
            title=title,
            expert=expert,
            source_language=source_language,
        )
        return _payload_from_record(saved, repo)

    if not raw_text:
        saved = repo.save_failure(
            video_id=video_id,
            status=TranscriptStatus.UNAVAILABLE,
            failure_code="empty_transcript",
            failure_reason="Transcript provider returned no text",
            video_url=video_url,
            title=title,
            expert=expert,
            source_language=source_language,
        )
        return _payload_from_record(saved, repo)

    saved = repo.save_available(
        video_id=video_id,
        transcript_text=clean_transcript(raw_text),
        video_url=video_url,
        title=title,
        expert=expert,
        source_language=source_language,
    )
    return _payload_from_record(saved, repo)


def _fetch_transcript_with_delay(
    video_id: str,
    *,
    proxy_settings: WebshareProxySettings | None = None,
) -> str:
    time.sleep(random.uniform(1.0, 3.0))
    return fetch_transcript(video_id, proxy_settings=proxy_settings)
