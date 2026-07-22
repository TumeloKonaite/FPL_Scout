from __future__ import annotations

import json
from pathlib import Path

from scripts.backfill_report_seasons import backfill_report_seasons


def _legacy_run(root: Path, run_id: str = "legacy") -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    final = {"gameweek": 12, "overview": "Overview", "conclusion": "Conclusion"}
    aggregate = {"gameweek": 12, "expert_count": 0}
    manifest = {"run_id": run_id, "gameweek": 12, "status": "completed"}
    for name, payload in (
        ("final_report.json", final),
        ("aggregate_report.json", aggregate),
        ("manifest.json", manifest),
    ):
        (run_dir / name).write_text(json.dumps(payload), encoding="utf-8")
    return run_dir


def test_dry_run_does_not_modify_files(tmp_path) -> None:
    run_dir = _legacy_run(tmp_path)
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}
    result = backfill_report_seasons(tmp_path, season="2025-26", dry_run=True)
    assert result.migrated == ["legacy"]
    assert {path.name: path.read_bytes() for path in run_dir.iterdir()} == before
    assert not (tmp_path / "index.json").exists()


def test_explicit_assignment_updates_all_artifacts_and_index(tmp_path) -> None:
    run_dir = _legacy_run(tmp_path)
    result = backfill_report_seasons(tmp_path, season="2025-26")
    assert result.migrated == ["legacy"]
    for name in ("final_report.json", "aggregate_report.json", "manifest.json"):
        payload = json.loads((run_dir / name).read_text(encoding="utf-8"))
        assert (payload["season"], payload["gameweek"]) == ("2025-26", 12)
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index[0]["season"] == "2025-26"
    assert index[0]["report_path"] == "legacy/final_report.json"


def test_existing_season_is_not_overwritten(tmp_path) -> None:
    run_dir = _legacy_run(tmp_path)
    final_path = run_dir / "final_report.json"
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final["season"] = "2024-25"
    final_path.write_text(json.dumps(final), encoding="utf-8")
    result = backfill_report_seasons(tmp_path, season="2025-26")
    assert result.skipped == ["legacy"]
    assert json.loads(final_path.read_text(encoding="utf-8"))["season"] == "2024-25"


def test_unknown_is_recorded_but_not_canonical(tmp_path) -> None:
    _legacy_run(tmp_path)
    result = backfill_report_seasons(tmp_path, season="unknown")
    assert result.migrated == ["legacy"]
    from src.app.infrastructure.storage.report_store import ReportStore

    assert ReportStore(tmp_path).get_report_for_gameweek("2025-26", 12) is None


def test_write_failure_restores_all_artifacts(monkeypatch, tmp_path) -> None:
    run_dir = _legacy_run(tmp_path)
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}

    def fail_index(*args, **kwargs):
        raise OSError("index unavailable")

    monkeypatch.setattr(
        "scripts.backfill_report_seasons.update_report_index", fail_index
    )
    result = backfill_report_seasons(tmp_path, season="2025-26")
    assert "legacy" in result.failed
    assert {path.name: path.read_bytes() for path in run_dir.iterdir()} == before
