from __future__ import annotations

import json
from pathlib import Path

from src.app.infrastructure.storage.report_store import ReportStore


def _write_run(
    root: Path,
    run_id: str,
    *,
    season: str,
    gameweek: int,
    status: str = "completed",
    updated_at: str = "2026-08-01T00:00:00Z",
) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "final_report.json").write_text(
        json.dumps({"season": season, "gameweek": gameweek}), encoding="utf-8"
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "season": season,
                "gameweek": gameweek,
                "status": status,
                "created_at": updated_at,
                "updated_at": updated_at,
            }
        ),
        encoding="utf-8",
    )


def test_same_gameweek_resolves_independently_across_seasons(tmp_path) -> None:
    _write_run(tmp_path, "old", season="2025-26", gameweek=1)
    _write_run(tmp_path, "new", season="2026-27", gameweek=1)
    store = ReportStore(tmp_path)
    assert store.get_report_for_gameweek("2025-26", 1).run_id == "old"
    assert store.get_report_for_gameweek("2026-27", 1).run_id == "new"
    assert store.get_report_for_gameweek("2027-28", 1) is None


def test_newest_completed_run_wins_and_failed_run_is_ignored(tmp_path) -> None:
    _write_run(
        tmp_path,
        "older",
        season="2026-27",
        gameweek=4,
        updated_at="2026-08-01T00:00:00Z",
    )
    _write_run(
        tmp_path,
        "newer",
        season="2026-27",
        gameweek=4,
        updated_at="2026-08-02T00:00:00Z",
    )
    _write_run(
        tmp_path,
        "failed",
        season="2026-27",
        gameweek=4,
        status="failed",
        updated_at="2026-08-03T00:00:00Z",
    )
    store = ReportStore(tmp_path)
    assert [
        record.run_id for record in store.get_reports_for_gameweek("2026-27", 4)
    ] == [
        "older",
        "newer",
        "failed",
    ]
    assert store.get_report_for_gameweek("2026-27", 4).run_id == "newer"


def test_equal_timestamps_use_run_id_deterministically(tmp_path) -> None:
    _write_run(tmp_path, "run-a", season="2026-27", gameweek=4)
    _write_run(tmp_path, "run-b", season="2026-27", gameweek=4)
    assert ReportStore(tmp_path).get_report_for_gameweek("2026-27", 4).run_id == "run-b"


def test_list_available_gameweeks_returns_one_canonical_run_per_identity(
    tmp_path,
) -> None:
    _write_run(tmp_path, "old-gw4", season="2026-27", gameweek=4)
    _write_run(
        tmp_path,
        "new-gw4",
        season="2026-27",
        gameweek=4,
        updated_at="2026-08-02T00:00:00Z",
    )
    _write_run(tmp_path, "gw3", season="2026-27", gameweek=3)
    _write_run(tmp_path, "old-season", season="2025-26", gameweek=38)
    _write_run(
        tmp_path,
        "incomplete",
        season="2027-28",
        gameweek=1,
        status="running",
    )

    records = ReportStore(tmp_path).list_available_gameweeks()

    assert [
        (record.season, record.gameweek, record.run_id) for record in records
    ] == [
        ("2026-27", 4, "new-gw4"),
        ("2026-27", 3, "gw3"),
        ("2025-26", 38, "old-season"),
    ]


def test_latest_crosses_season_boundary_and_can_prefer_current_identity(
    tmp_path,
) -> None:
    _write_run(
        tmp_path,
        "gw38",
        season="2025-26",
        gameweek=38,
        updated_at="2026-05-20T00:00:00Z",
    )
    _write_run(
        tmp_path, "gw1", season="2026-27", gameweek=1, updated_at="2026-08-01T00:00:00Z"
    )
    _write_run(
        tmp_path,
        "later-file",
        season="2025-26",
        gameweek=20,
        updated_at="2026-09-01T00:00:00Z",
    )
    store = ReportStore(tmp_path)
    assert store.get_latest_report().run_id == "later-file"
    assert store.get_latest_report("2026-27", 1).run_id == "gw1"


def test_unknown_and_inconsistent_runs_are_not_canonical(tmp_path) -> None:
    _write_run(tmp_path, "classified", season="2025-26", gameweek=38)
    _write_run(
        tmp_path,
        "unknown",
        season="unknown",
        gameweek=1,
        updated_at="2027-01-01T00:00:00Z",
    )
    _write_run(
        tmp_path,
        "mismatch",
        season="2026-27",
        gameweek=1,
        updated_at="2027-02-01T00:00:00Z",
    )
    mismatch = tmp_path / "mismatch" / "final_report.json"
    mismatch.write_text(
        json.dumps({"season": "2025-26", "gameweek": 1}), encoding="utf-8"
    )
    assert ReportStore(tmp_path).get_latest_report().run_id == "classified"
