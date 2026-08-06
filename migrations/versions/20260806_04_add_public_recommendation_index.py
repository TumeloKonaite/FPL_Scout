"""index lightweight public recommendation lookups"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_04"
down_revision = "20260727_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_completed_report_runs_public_recommendation",
        "completed_report_runs",
        [
            "season",
            "gameweek",
            sa.literal_column("updated_at DESC"),
            sa.literal_column("run_id DESC"),
        ],
        postgresql_where=sa.text("status = 'completed' AND final_report IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_completed_report_runs_public_recommendation",
        table_name="completed_report_runs",
    )
