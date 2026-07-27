"""persist reports and pipeline runs in PostgreSQL"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260727_02"
down_revision = "20260721_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("current_stage", sa.String(128)),
        sa.Column("input_data", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float()),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_pipeline_runs_status",
        ),
    )
    op.create_index("ix_pipeline_runs_status_updated_at", "pipeline_runs", ["status", "updated_at"])
    op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])
    op.create_index(
        "uq_pipeline_runs_single_active",
        "pipeline_runs",
        [sa.literal_column("(1)")],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )

    op.create_table(
        "completed_report_runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            sa.String(64),
            sa.ForeignKey("pipeline_runs.run_id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("season", sa.String(7), nullable=False),
        sa.Column("gameweek", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("discovered_videos", postgresql.JSONB(), nullable=False),
        sa.Column("input_jobs", postgresql.JSONB(), nullable=False),
        sa.Column("expert_outputs", postgresql.JSONB(), nullable=False),
        sa.Column("failed_jobs", postgresql.JSONB(), nullable=False),
        sa.Column("duplicate_sources", postgresql.JSONB(), nullable=False),
        sa.Column("transcript_failures", postgresql.JSONB(), nullable=False),
        sa.Column("aggregate_report", postgresql.JSONB(), nullable=False),
        sa.Column("final_report", postgresql.JSONB(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("rendered_markdown", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'invalid')",
            name="ck_completed_report_runs_status",
        ),
        sa.CheckConstraint(
            "gameweek >= 1 AND gameweek <= 38",
            name="ck_completed_report_runs_gameweek",
        ),
    )
    op.create_index(
        "ix_completed_report_runs_season_gameweek",
        "completed_report_runs",
        ["season", "gameweek", "updated_at"],
    )
    op.create_index(
        "ix_completed_report_runs_completed_updated",
        "completed_report_runs",
        ["status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_table("completed_report_runs")
    op.drop_table("pipeline_runs")
