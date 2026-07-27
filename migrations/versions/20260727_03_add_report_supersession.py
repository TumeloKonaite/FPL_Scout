"""add historical report supersession and regeneration audit metadata"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_03"
down_revision = "20260727_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_completed_report_runs_status",
        "completed_report_runs",
        type_="check",
    )
    op.add_column(
        "completed_report_runs",
        sa.Column("superseded_by_run_id", sa.String(64)),
    )
    op.add_column(
        "completed_report_runs",
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "completed_report_runs",
        sa.Column("supersession_reason", sa.Text()),
    )
    op.create_unique_constraint(
        "uq_completed_report_runs_identity_target",
        "completed_report_runs",
        ["run_id", "season", "gameweek"],
    )
    op.create_foreign_key(
        "fk_completed_report_runs_superseded_by_identity",
        "completed_report_runs",
        "completed_report_runs",
        ["superseded_by_run_id", "season", "gameweek"],
        ["run_id", "season", "gameweek"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_status",
        "completed_report_runs",
        "status IN ('processing', 'completed', 'invalid', 'superseded')",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        "("
        "status = 'superseded' AND superseded_by_run_id IS NOT NULL "
        "AND superseded_at IS NOT NULL AND supersession_reason IS NOT NULL"
        ") OR ("
        "status != 'superseded' AND superseded_by_run_id IS NULL "
        "AND superseded_at IS NULL AND supersession_reason IS NULL"
        ")",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_no_self_supersession",
        "completed_report_runs",
        "superseded_by_run_id IS NULL OR superseded_by_run_id != run_id",
    )

    op.create_table(
        "historical_regeneration_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("season", sa.String(7), nullable=False),
        sa.Column("gameweek", sa.Integer(), nullable=False),
        sa.Column("previous_run_id", sa.String(64)),
        sa.Column(
            "replacement_run_id",
            sa.String(64),
            sa.ForeignKey("completed_report_runs.run_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(16)),
        sa.Column("replacement_status", sa.String(16), nullable=False),
        sa.Column(
            "historical_deadline",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("selected_video_fingerprint", sa.String(64), nullable=False),
        sa.Column("validation_rule_version", sa.String(32), nullable=False),
        sa.Column("batch_identifier", sa.String(128), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("audit_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "gameweek >= 1 AND gameweek <= 38",
            name="ck_historical_regeneration_audits_gameweek",
        ),
    )
    op.create_index(
        "ix_historical_regeneration_audits_identity",
        "historical_regeneration_audits",
        ["season", "gameweek", "generated_at"],
    )
    op.create_index(
        "ix_historical_regeneration_audits_batch",
        "historical_regeneration_audits",
        ["batch_identifier"],
    )


def downgrade() -> None:
    op.drop_table("historical_regeneration_audits")
    op.drop_constraint(
        "ck_completed_report_runs_no_self_supersession",
        "completed_report_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_completed_report_runs_status",
        "completed_report_runs",
        type_="check",
    )
    op.drop_constraint(
        "fk_completed_report_runs_superseded_by_identity",
        "completed_report_runs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_completed_report_runs_identity_target",
        "completed_report_runs",
        type_="unique",
    )
    op.drop_column("completed_report_runs", "supersession_reason")
    op.drop_column("completed_report_runs", "superseded_at")
    op.drop_column("completed_report_runs", "superseded_by_run_id")
    op.create_check_constraint(
        "ck_completed_report_runs_status",
        "completed_report_runs",
        "status IN ('processing', 'completed', 'invalid')",
    )
