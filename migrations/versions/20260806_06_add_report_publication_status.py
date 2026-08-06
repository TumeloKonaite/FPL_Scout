"""add explicit completed-report publication state

Existing valid completed reports are ranked per season/gameweek by updated_at,
created_at, and run_id (all descending).  The first is published and the other
valid completed snapshots are superseded.  Non-completed and payload-less rows
remain unpublished before the unique partial index is installed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260806_06"
down_revision = "20260806_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "completed_report_runs",
        sa.Column(
            "publication_status",
            sa.String(16),
            nullable=True,
            server_default=sa.text("'unpublished'"),
        ),
    )
    # A null payload must be representable so the publication operation can
    # reject it explicitly and keep the snapshot unpublished.
    op.alter_column(
        "completed_report_runs",
        "final_report",
        existing_type=postgresql.JSONB(),
        nullable=True,
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                run_id,
                row_number() OVER (
                    PARTITION BY season, gameweek
                    ORDER BY updated_at DESC, created_at DESC, run_id DESC
                ) AS publication_rank
            FROM completed_report_runs
            WHERE status = 'completed'
              AND final_report IS NOT NULL
        )
        UPDATE completed_report_runs AS report
        SET publication_status = CASE
            WHEN ranked.publication_rank = 1 THEN 'published'
            WHEN report.status = 'completed'
                 AND report.final_report IS NOT NULL THEN 'superseded'
            WHEN report.status = 'superseded' THEN 'superseded'
            ELSE 'unpublished'
        END
        FROM (
            SELECT candidate.run_id, candidate.publication_rank
            FROM ranked AS candidate
            UNION ALL
            SELECT unranked.run_id, NULL::bigint
            FROM completed_report_runs AS unranked
            WHERE NOT EXISTS (
                SELECT 1 FROM ranked WHERE ranked.run_id = unranked.run_id
            )
        ) AS ranked
        WHERE report.run_id = ranked.run_id
        """
    )
    op.alter_column(
        "completed_report_runs",
        "publication_status",
        existing_type=sa.String(16),
        nullable=False,
        server_default=sa.text("'unpublished'"),
    )

    op.drop_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        "(superseded_by_run_id IS NULL AND superseded_at IS NULL "
        "AND supersession_reason IS NULL) OR "
        "(publication_status = 'superseded' "
        "AND superseded_by_run_id IS NOT NULL "
        "AND superseded_at IS NOT NULL AND supersession_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_publication_status",
        "completed_report_runs",
        "publication_status IN ('published', 'superseded', 'unpublished')",
    )
    op.create_check_constraint(
        "ck_completed_report_runs_published_is_valid",
        "completed_report_runs",
        "publication_status != 'published' OR "
        "(status = 'completed' AND final_report IS NOT NULL)",
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM completed_report_runs
                WHERE publication_status IS NULL
                   OR publication_status NOT IN (
                       'published', 'superseded', 'unpublished'
                   )
            ) THEN
                RAISE EXCEPTION 'publication backfill left invalid states';
            END IF;
            IF EXISTS (
                SELECT season, gameweek
                FROM completed_report_runs
                WHERE publication_status = 'published'
                GROUP BY season, gameweek
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'publication backfill left duplicate published reports';
            END IF;
        END
        $$
        """
    )

    op.drop_index(
        "ix_completed_report_runs_public_recommendation",
        table_name="completed_report_runs",
    )
    op.drop_index(
        "ix_completed_report_public_lookup",
        table_name="completed_report_runs",
    )
    op.create_index(
        "uq_published_report_per_gameweek",
        "completed_report_runs",
        ["season", "gameweek"],
        unique=True,
        postgresql_where=sa.text("publication_status = 'published'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_published_report_per_gameweek",
        table_name="completed_report_runs",
    )
    op.create_index(
        "ix_completed_report_runs_public_recommendation",
        "completed_report_runs",
        [
            "season",
            "gameweek",
            sa.literal_column("updated_at DESC"),
            sa.literal_column("run_id DESC"),
        ],
        postgresql_where=sa.text(
            "status = 'completed' AND final_report IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_completed_report_public_lookup",
        "completed_report_runs",
        ["season", "gameweek", sa.literal_column("updated_at DESC")],
        postgresql_where=sa.text("status = 'completed'"),
    )

    op.drop_constraint(
        "ck_completed_report_runs_published_is_valid",
        "completed_report_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_completed_report_runs_publication_status",
        "completed_report_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        type_="check",
    )
    op.execute(
        """
        UPDATE completed_report_runs
        SET status = 'superseded'
        WHERE status = 'completed'
          AND publication_status = 'superseded'
          AND superseded_by_run_id IS NOT NULL
          AND superseded_at IS NOT NULL
          AND supersession_reason IS NOT NULL
        """
    )
    op.create_check_constraint(
        "ck_completed_report_runs_supersession_fields",
        "completed_report_runs",
        "(status = 'superseded' AND superseded_by_run_id IS NOT NULL "
        "AND superseded_at IS NOT NULL AND supersession_reason IS NOT NULL) "
        "OR (status != 'superseded' AND superseded_by_run_id IS NULL "
        "AND superseded_at IS NULL AND supersession_reason IS NULL)",
    )
    op.drop_column("completed_report_runs", "publication_status")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM completed_report_runs WHERE final_report IS NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot restore final_report NOT NULL while null snapshots exist';
            END IF;
        END
        $$
        """
    )
    op.alter_column(
        "completed_report_runs",
        "final_report",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )
