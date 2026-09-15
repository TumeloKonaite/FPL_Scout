"""add expiring leases to pipeline runs"""

from alembic import op
import sqlalchemy as sa


revision = "20260915_08"
down_revision = "20260806_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        "UPDATE pipeline_runs SET heartbeat_at = updated_at, "
        "lease_expires_at = updated_at + CASE "
        "WHEN status = 'queued' THEN interval '15 minutes' "
        "ELSE interval '5 minutes' END "
        "WHERE status IN ('queued', 'running')"
    )
    op.create_index(
        "ix_pipeline_runs_active_lease",
        "pipeline_runs",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_active_lease", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "lease_expires_at")
    op.drop_column("pipeline_runs", "heartbeat_at")
