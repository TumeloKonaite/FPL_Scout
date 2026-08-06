from __future__ import annotations

from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260806_07_add_gameweek_index_metadata.py"
)


def test_migration_backfills_selector_metadata_before_making_it_required() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert '"has_report"' in source
    assert '"has_suggested_team"' in source
    assert "UPDATE completed_report_runs" in source
    assert "jsonb_array_length" in source
    assert source.index("UPDATE completed_report_runs") < source.index(
        "nullable=False"
    )
