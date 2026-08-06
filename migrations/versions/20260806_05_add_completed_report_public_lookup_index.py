"""add the concurrent completed-report public lookup index"""

from alembic import op


revision = "20260806_05"
down_revision = "20260806_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
                ix_completed_report_public_lookup
            ON completed_report_runs (
                season,
                gameweek,
                updated_at DESC
            )
            WHERE status = 'completed'
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            DROP INDEX CONCURRENTLY IF EXISTS
                ix_completed_report_public_lookup
            """
        )
