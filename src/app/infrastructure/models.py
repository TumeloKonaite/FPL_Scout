from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptStatus(str, enum.Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


status_type = Enum(
    TranscriptStatus,
    values_callable=lambda enum_class: [item.value for item in enum_class],
    native_enum=False,
    create_constraint=True,
    length=16,
    name="transcript_status",
)


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint("video_id", name="uq_transcripts_video_id"),
        CheckConstraint(
            "status != 'available' OR transcript_text IS NOT NULL",
            name="ck_transcripts_available_has_text",
        ),
        Index("ix_transcripts_status", "status"),
        Index("ix_transcripts_updated_at", "updated_at"),
        Index("ix_transcripts_fetched_at", "fetched_at"),
        Index("ix_transcripts_video_id", "video_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(512))
    expert: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[TranscriptStatus] = mapped_column(status_type, nullable=False)
    transcript_text: Mapped[str | None] = mapped_column(Text)
    source_language: Mapped[str | None] = mapped_column(String(32))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(),
        onupdate=_utc_now, nullable=False
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))

    revisions: Mapped[list[TranscriptRevision]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )


class TranscriptRevision(Base):
    __tablename__ = "transcript_revisions"
    __table_args__ = (
        Index("ix_transcript_revisions_transcript_id", "transcript_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    transcript_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[TranscriptStatus] = mapped_column(status_type, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(String(128))
    source_language: Mapped[str | None] = mapped_column(String(32))
    revision_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    transcript: Mapped[Transcript] = relationship(back_populates="revisions")
