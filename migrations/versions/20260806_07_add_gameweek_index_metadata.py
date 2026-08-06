"""add relational metadata for the public gameweek index"""

from alembic import op
import sqlalchemy as sa


revision = "20260806_07"
down_revision = "20260806_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "completed_report_runs",
        sa.Column(
            "has_report",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "completed_report_runs",
        sa.Column(
            "has_suggested_team",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    # Backfill the legacy shape conservatively.  New and rewritten snapshots use
    # the application validator to populate this field exactly.  Historical rows
    # only qualify when they contain the complete 11-player XI and four-player
    # bench required by the selector's previous validation path.
    op.execute(
        """
        UPDATE completed_report_runs
        SET
            has_report = COALESCE(
                jsonb_typeof(final_report) = 'object'
                AND jsonb_typeof(final_report -> 'season') = 'string'
                AND jsonb_typeof(final_report -> 'gameweek') = 'number'
                AND jsonb_typeof(final_report -> 'overview') = 'string'
                AND jsonb_typeof(final_report -> 'conclusion') = 'string',
                false
            ),
            has_suggested_team = CASE
                WHEN jsonb_typeof(
                    final_report -> 'suggested_team' -> 'startingXi'
                ) = 'array'
                AND jsonb_typeof(
                    final_report -> 'suggested_team' -> 'bench'
                ) = 'array'
                THEN
                    jsonb_array_length(
                        final_report -> 'suggested_team' -> 'startingXi'
                    ) = 11
                    AND jsonb_array_length(
                        final_report -> 'suggested_team' -> 'bench'
                    ) = 4
                    AND COALESCE(
                        final_report -> 'suggested_team'
                            ->> 'constructionStatus',
                        'consensus'
                    ) = 'consensus'
                    AND NULLIF(
                        final_report -> 'suggested_team' ->> 'failureReason',
                        ''
                    ) IS NULL
                ELSE false
            END
        """
    )
    op.alter_column(
        "completed_report_runs",
        "has_report",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.alter_column(
        "completed_report_runs",
        "has_suggested_team",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.drop_column("completed_report_runs", "has_suggested_team")
    op.drop_column("completed_report_runs", "has_report")
