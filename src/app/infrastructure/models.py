from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))

    revisions: Mapped[list[TranscriptRevision]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )


class TranscriptRevision(Base):
    __tablename__ = "transcript_revisions"
    __table_args__ = (Index("ix_transcript_revisions_transcript_id", "transcript_id"),)

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
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )

    transcript: Mapped[Transcript] = relationship(back_populates="revisions")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_pipeline_runs_status",
        ),
        Index("ix_pipeline_runs_status_updated_at", "status", "updated_at"),
        Index("ix_pipeline_runs_created_at", "created_at"),
        # PostgreSQL enforces pipeline exclusivity across every API/worker process.
        Index(
            "uq_pipeline_runs_single_active",
            text("(1)"),
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(128))
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    report: Mapped[CompletedReportRun | None] = relationship(
        back_populates="pipeline_run"
    )


class CompletedReportRun(Base):
    __tablename__ = "completed_report_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'invalid', 'superseded')",
            name="ck_completed_report_runs_status",
        ),
        CheckConstraint(
            "(superseded_by_run_id IS NULL AND superseded_at IS NULL "
            "AND supersession_reason IS NULL) OR "
            "(publication_status = 'superseded' "
            "AND superseded_by_run_id IS NOT NULL "
            "AND superseded_at IS NOT NULL AND supersession_reason IS NOT NULL)",
            name="ck_completed_report_runs_supersession_fields",
        ),
        CheckConstraint(
            "publication_status IN ('published', 'superseded', 'unpublished')",
            name="ck_completed_report_runs_publication_status",
        ),
        CheckConstraint(
            "publication_status != 'published' OR "
            "(status = 'completed' AND final_report IS NOT NULL)",
            name="ck_completed_report_runs_published_is_valid",
        ),
        CheckConstraint(
            "superseded_by_run_id IS NULL OR superseded_by_run_id != run_id",
            name="ck_completed_report_runs_no_self_supersession",
        ),
        UniqueConstraint(
            "run_id",
            "season",
            "gameweek",
            name="uq_completed_report_runs_identity_target",
        ),
        ForeignKeyConstraint(
            ["superseded_by_run_id", "season", "gameweek"],
            [
                "completed_report_runs.run_id",
                "completed_report_runs.season",
                "completed_report_runs.gameweek",
            ],
            name="fk_completed_report_runs_superseded_by_identity",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "gameweek >= 1 AND gameweek <= 38",
            name="ck_completed_report_runs_gameweek",
        ),
        Index(
            "ix_completed_report_runs_season_gameweek",
            "season",
            "gameweek",
            "updated_at",
        ),
        Index(
            "ix_completed_report_runs_completed_updated",
            "status",
            "updated_at",
        ),
        Index(
            "uq_published_report_per_gameweek",
            "season",
            "gameweek",
            unique=True,
            postgresql_where=text("publication_status = 'published'"),
        ),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("pipeline_runs.run_id", ondelete="RESTRICT"), unique=True
    )
    season: Mapped[str] = mapped_column(String(7), nullable=False)
    gameweek: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    publication_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="unpublished",
        server_default=text("'unpublished'"),
    )
    # Derived from final_report when a snapshot is written.  final_report is the
    # source of truth; these relational copies exist only for lightweight indexes.
    has_report: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    has_suggested_team: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    discovered_videos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    input_jobs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expert_outputs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    failed_jobs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    duplicate_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    transcript_failures: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    aggregate_report: Mapped[dict] = mapped_column(JSONB, nullable=False)
    final_report: Mapped[dict | None] = mapped_column(JSONB)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rendered_markdown: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_run_id: Mapped[str | None] = mapped_column(String(64))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersession_reason: Mapped[str | None] = mapped_column(Text)

    pipeline_run: Mapped[PipelineRun | None] = relationship(back_populates="report")


class HistoricalRegenerationAudit(Base):
    __tablename__ = "historical_regeneration_audits"
    __table_args__ = (
        CheckConstraint(
            "gameweek >= 1 AND gameweek <= 38",
            name="ck_historical_regeneration_audits_gameweek",
        ),
        Index(
            "ix_historical_regeneration_audits_identity",
            "season",
            "gameweek",
            "generated_at",
        ),
        Index(
            "ix_historical_regeneration_audits_batch",
            "batch_identifier",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    season: Mapped[str] = mapped_column(String(7), nullable=False)
    gameweek: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_run_id: Mapped[str | None] = mapped_column(String(64))
    replacement_run_id: Mapped[str] = mapped_column(
        ForeignKey("completed_report_runs.run_id", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(16))
    replacement_status: Mapped[str] = mapped_column(String(16), nullable=False)
    historical_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    selected_video_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    audit_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
