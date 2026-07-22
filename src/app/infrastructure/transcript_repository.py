from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.app.core.config import get_settings
from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import Transcript, TranscriptRevision, TranscriptStatus
from src.utils.text_cleaning import clean_transcript

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _revision_key(
    *,
    content_hash: str | None,
    status: TranscriptStatus,
    failure_code: str | None,
    failure_reason: str | None,
    source_language: str | None,
) -> str:
    value = json.dumps(
        [content_hash, status.value, failure_code, failure_reason, source_language],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sanitize_failure_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return " ".join(reason.split())[:2000]


class TranscriptRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        retry_hours: int | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self.retry_hours = (
            get_settings().TRANSCRIPT_FAILURE_RETRY_HOURS
            if retry_hours is None
            else retry_hours
        )
        self._now = now

    def get_by_video_id(self, video_id: str) -> Transcript | None:
        with self._session_factory() as session:
            return session.scalar(select(Transcript).where(Transcript.video_id == video_id))

    def update_metadata(
        self,
        video_id: str,
        *,
        video_url: str | None = None,
        title: str | None = None,
        expert: str | None = None,
    ) -> Transcript | None:
        with self._session_factory.begin() as session:
            record = session.scalar(
                select(Transcript)
                .where(Transcript.video_id == video_id)
                .with_for_update()
            )
            if record is None:
                return None
            for name, value in {
                "video_url": video_url,
                "title": title,
                "expert": expert,
            }.items():
                if value is not None:
                    setattr(record, name, value)
            session.flush()
            return record

    def save_available(
        self,
        *,
        video_id: str,
        transcript_text: str,
        video_url: str | None = None,
        title: str | None = None,
        expert: str | None = None,
        source_language: str | None = None,
    ) -> Transcript:
        normalized = clean_transcript(transcript_text)
        if not normalized:
            raise ValueError("An available transcript must contain text")
        return self._save(
            video_id=video_id,
            status=TranscriptStatus.AVAILABLE,
            transcript_text=normalized,
            content_hash=_content_hash(normalized),
            video_url=video_url,
            title=title,
            expert=expert,
            source_language=source_language,
            failure_code=None,
            failure_reason=None,
        )

    def save_failure(
        self,
        *,
        video_id: str,
        status: TranscriptStatus,
        failure_code: str | None,
        failure_reason: str | None,
        video_url: str | None = None,
        title: str | None = None,
        expert: str | None = None,
        source_language: str | None = None,
    ) -> Transcript:
        if status not in {TranscriptStatus.UNAVAILABLE, TranscriptStatus.FAILED}:
            raise ValueError("Failure status must be unavailable or failed")
        return self._save(
            video_id=video_id,
            status=status,
            transcript_text=None,
            content_hash=None,
            video_url=video_url,
            title=title,
            expert=expert,
            source_language=source_language,
            failure_code=failure_code,
            failure_reason=_sanitize_failure_reason(failure_reason),
        )

    def _save(self, **values) -> Transcript:
        # A unique video_id plus retry-on-conflict makes simultaneous first writes safe.
        for attempt in range(2):
            try:
                with self._session_factory.begin() as session:
                    record = session.scalar(
                        select(Transcript)
                        .where(Transcript.video_id == values["video_id"])
                        .with_for_update()
                    )
                    now = self._now()
                    if record is None:
                        record = Transcript(**values, fetched_at=now)
                        session.add(record)
                        session.flush()
                        logger.info(
                            "transcript inserted", extra={"video_id": values["video_id"]}
                        )
                    else:
                        for name, value in values.items():
                            if name == "video_id":
                                continue
                            # Do not erase useful discovery metadata when a caller omits it.
                            if name in {"video_url", "title", "expert"} and value is None:
                                continue
                            setattr(record, name, value)
                        record.fetched_at = now
                        logger.info(
                            "transcript updated", extra={"video_id": values["video_id"]}
                        )

                    key = _revision_key(
                        content_hash=record.content_hash,
                        status=record.status,
                        failure_code=record.failure_code,
                        failure_reason=record.failure_reason,
                        source_language=record.source_language,
                    )
                    latest_key = session.scalar(
                        select(TranscriptRevision.revision_key)
                        .where(TranscriptRevision.transcript_id == record.id)
                        .order_by(
                            TranscriptRevision.created_at.desc(),
                            TranscriptRevision.id.desc(),
                        )
                        .limit(1)
                    )
                    if latest_key != key:
                        session.add(
                            TranscriptRevision(
                                transcript_id=record.id,
                                transcript_text=record.transcript_text,
                                content_hash=record.content_hash,
                                status=record.status,
                                failure_reason=record.failure_reason,
                                failure_code=record.failure_code,
                                source_language=record.source_language,
                                revision_key=key,
                            )
                        )
                        logger.info(
                            "transcript revision created",
                            extra={"video_id": values["video_id"]},
                        )
                    session.flush()
                    return record
            except IntegrityError:
                if attempt:
                    raise
        raise RuntimeError("Could not persist transcript")

    def get_current_revision(self, transcript_id) -> TranscriptRevision | None:
        with self._session_factory() as session:
            return session.scalar(
                select(TranscriptRevision)
                .where(TranscriptRevision.transcript_id == transcript_id)
                .order_by(TranscriptRevision.created_at.desc(), TranscriptRevision.id.desc())
                .limit(1)
            )

    def list_history(self, transcript_id) -> list[TranscriptRevision]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(TranscriptRevision)
                    .where(TranscriptRevision.transcript_id == transcript_id)
                    .order_by(TranscriptRevision.created_at, TranscriptRevision.id)
                )
            )

    def should_retry(self, transcript: Transcript) -> bool:
        if transcript.status == TranscriptStatus.AVAILABLE:
            return False
        fetched_at = transcript.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return self._now() >= fetched_at + timedelta(hours=self.retry_hours)
