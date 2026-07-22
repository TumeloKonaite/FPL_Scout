"""add transcripts and transcript revisions"""

from alembic import op
import sqlalchemy as sa

revision = "20260721_01"
down_revision = None
branch_labels = None
depends_on = None

status = sa.Enum(
    "available", "unavailable", "failed", name="transcript_status",
    native_enum=False, create_constraint=True, length=16,
)


def upgrade() -> None:
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.String(32), nullable=False),
        sa.Column("video_url", sa.String(2048)),
        sa.Column("title", sa.String(512)),
        sa.Column("expert", sa.String(255)),
        sa.Column("status", status, nullable=False),
        sa.Column("transcript_text", sa.Text()),
        sa.Column("source_language", sa.String(32)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("failure_code", sa.String(128)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.CheckConstraint("status != 'available' OR transcript_text IS NOT NULL", name="ck_transcripts_available_has_text"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", name="uq_transcripts_video_id"),
    )
    op.create_index("ix_transcripts_video_id", "transcripts", ["video_id"])
    op.create_index("ix_transcripts_status", "transcripts", ["status"])
    op.create_index("ix_transcripts_updated_at", "transcripts", ["updated_at"])
    op.create_index("ix_transcripts_fetched_at", "transcripts", ["fetched_at"])
    op.create_table(
        "transcript_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_text", sa.Text()),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("status", status, nullable=False),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("failure_code", sa.String(128)),
        sa.Column("source_language", sa.String(32)),
        sa.Column("revision_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_revisions_transcript_id", "transcript_revisions", ["transcript_id"])


def downgrade() -> None:
    op.drop_table("transcript_revisions")
    op.drop_table("transcripts")
