from __future__ import annotations

import logging
import random
import time
from pathlib import Path

from src.adapters.storage import load_transcript, save_transcript
from src.adapters.transcript_api import TranscriptFetchError, WebshareProxySettings, fetch_transcript
from src.app.core.config import get_settings
from src.app.infrastructure.models import Transcript, TranscriptStatus
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.utils.retry import RetryConfig, RetryError, retry_call
from src.utils.text_cleaning import clean_transcript

logger = logging.getLogger(__name__)


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
    save_transcript(str(_build_transcript_cache_path(video_id, cache_dir)), payload)


def _sleep_before_transcript_fetch() -> None:
    time.sleep(random.uniform(1.0, 3.0))


def _default_repository() -> TranscriptRepository | None:
    settings = get_settings()
    if settings.TRANSCRIPT_STORE.casefold() != "postgres" or not settings.DATABASE_URL.strip():
        return None
    return TranscriptRepository(retry_hours=settings.TRANSCRIPT_FAILURE_RETRY_HOURS)


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
    settings = get_settings()
    resolved_cache_dir = cache_dir or settings.TRANSCRIPTS_DIR
    resolved_repository = repository
    database_failed = False
    database_miss = False
    if resolved_repository is None:
        try:
            resolved_repository = _default_repository()
        except Exception:
            database_failed = True
            logger.exception("transcript database initialization failed", extra={"video_id": video_id})

    if resolved_repository is not None:
        try:
            record = resolved_repository.get_by_video_id(video_id)
            database_miss = record is None
            if record is not None and record.status == TranscriptStatus.AVAILABLE:
                logger.info("transcript database cache hit", extra={"video_id": video_id})
                return _payload_from_record(record, resolved_repository)
            if record is not None and not resolved_repository.should_retry(record):
                logger.info("unavailable transcript reused", extra={"video_id": video_id})
                return _payload_from_record(record, resolved_repository)
            logger.info(
                "failed transcript retry" if record is not None else "transcript database cache miss",
                extra={"video_id": video_id},
            )
        except Exception:
            database_failed = True
            logger.exception("transcript database lookup failed", extra={"video_id": video_id})

    use_file_fallback = (
        resolved_repository is None or database_failed or database_miss
    ) and settings.TRANSCRIPT_FILE_FALLBACK_ENABLED
    if use_file_fallback:
        cached_payload = _load_cached_transcript(video_id, resolved_cache_dir)
        if cached_payload is not None:
            logger.info("legacy transcript file fallback used", extra={"video_id": video_id})
            if resolved_repository is not None and not database_failed:
                try:
                    record = resolved_repository.save_available(
                        video_id=video_id,
                        transcript_text=cached_payload["transcript"],
                        video_url=video_url,
                        title=title,
                        expert=expert,
                        source_language=source_language,
                    )
                    return _payload_from_record(record, resolved_repository)
                except Exception:
                    logger.exception(
                        "legacy transcript import failed", extra={"video_id": video_id}
                    )
            return cached_payload

    logger.info("YouTube transcript fetch", extra={"video_id": video_id})
    try:
        raw_text = retry_call(
            lambda: _fetch_transcript_with_delay(video_id, proxy_settings=proxy_settings),
            retry_on=(TranscriptFetchError,),
            context=f"Transcript fetch for video '{video_id}'",
            config=RetryConfig(max_attempts=3, initial_delay_seconds=0.1),
        )
    except RetryError as exc:
        error = str(exc)
        if resolved_repository is not None and not database_failed:
            try:
                record = resolved_repository.save_failure(
                    video_id=video_id, status=TranscriptStatus.FAILED,
                    failure_code="youtube_fetch_failed", failure_reason=error,
                    video_url=video_url, title=title, expert=expert,
                    source_language=source_language,
                )
                return _payload_from_record(record, resolved_repository)
            except Exception:
                logger.exception("transcript database persistence failed", extra={"video_id": video_id})
        return {"video_id": video_id, "transcript": "", "status": "error", "error": error}

    if not raw_text:
        if resolved_repository is not None and not database_failed:
            try:
                record = resolved_repository.save_failure(
                    video_id=video_id, status=TranscriptStatus.UNAVAILABLE,
                    failure_code="empty_transcript",
                    failure_reason="Transcript provider returned no text",
                    video_url=video_url, title=title, expert=expert,
                    source_language=source_language,
                )
                return _payload_from_record(record, resolved_repository)
            except Exception:
                logger.exception("transcript database persistence failed", extra={"video_id": video_id})
        return {"video_id": video_id, "transcript": "", "status": "missing"}

    cleaned = clean_transcript(raw_text)
    payload = {"video_id": video_id, "transcript": cleaned, "status": "available"}
    if resolved_repository is not None and not database_failed:
        try:
            record = resolved_repository.save_available(
                video_id=video_id, transcript_text=cleaned, video_url=video_url,
                title=title, expert=expert, source_language=source_language,
            )
            logger.info("transcript persisted", extra={"video_id": video_id})
            return _payload_from_record(record, resolved_repository)
        except Exception:
            logger.exception("transcript database persistence failed", extra={"video_id": video_id})
            if settings.TRANSCRIPT_FILE_FALLBACK_ENABLED:
                _save_cached_transcript(video_id, payload, resolved_cache_dir)
                return payload
    if use_file_fallback:
        _save_cached_transcript(video_id, payload, resolved_cache_dir)
    return payload


def _fetch_transcript_with_delay(
    video_id: str,
    *,
    proxy_settings: WebshareProxySettings | None = None,
) -> str:
    _sleep_before_transcript_fetch()
    return fetch_transcript(video_id, proxy_settings=proxy_settings)
