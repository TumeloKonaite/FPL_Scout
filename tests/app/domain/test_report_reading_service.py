from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.app.domain.reports.service import ReportService
from src.app.infrastructure.storage.report_store import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportStore,
)


def _final_report_payload(gameweek: int) -> dict:
    return {
        "season": "2025-26",
        "gameweek": gameweek,
        "overview": "Overview",
        "transfers": [],
        "captaincy": [],
        "chip_strategy": [],
        "fixture_notes": [],
        "disagreements": [],
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
        "conclusion": "Conclusion",
    }


def _aggregate_report_payload(gameweek: int) -> dict:
    return {
        "season": "2025-26",
        "gameweek": gameweek,
        "expert_count": 2,
        "player_consensus": [],
        "captaincy_consensus": [],
        "transfer_consensus": [],
        "fixture_insights": [],
        "chip_strategy_consensus": [],
        "disagreements": {"players": [], "captaincy": [], "strategy": []},
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
    }


def _write_report(run_dir: Path, gameweek: int, with_aggregate: bool = False) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final_report.json").write_text(
        json.dumps(_final_report_payload(gameweek)),
        encoding="utf-8",
    )
    if with_aggregate:
        (run_dir / "aggregate_report.json").write_text(
            json.dumps(_aggregate_report_payload(gameweek)),
            encoding="utf-8",
        )


def _service(base_dir: Path) -> ReportService:
    return ReportService(ReportStore(base_dir))


def test_list_reports_returns_report_summaries(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    _write_report(runs_dir / "gw31", gameweek=31)
    _write_report(runs_dir / "gw32", gameweek=32)

    reports = _service(runs_dir).list_reports()

    assert [report.run_id for report in reports] == ["gw31", "gw32"]
    assert reports[0].final_report_path == runs_dir / "gw31" / "final_report.json"


def test_get_latest_report_uses_latest_final_report_timestamp(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    older = runs_dir / "gw31"
    newer = runs_dir / "gw32"
    _write_report(older, gameweek=31)
    _write_report(newer, gameweek=32)
    os.utime(older / "final_report.json", (1_700_000_000, 1_700_000_000))
    os.utime(newer / "final_report.json", (1_700_000_100, 1_700_000_100))

    report = _service(runs_dir).get_latest_report()

    assert report.run_id == "gw32"
    assert report.final_report.gameweek == 32


def test_get_report_loads_specific_run_by_run_id(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    _write_report(runs_dir / "gw32", gameweek=32, with_aggregate=True)

    report = _service(runs_dir).get_report("gw32")

    assert report.run_dir == runs_dir / "gw32"
    assert report.final_report.gameweek == 32
    assert report.aggregate_report is not None
    assert report.aggregate_report.expert_count == 2


def test_empty_report_directory_handling(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    with pytest.raises(EmptyReportDirectoryError):
        _service(runs_dir).list_reports()


def test_missing_report_directory_handling(tmp_path) -> None:
    with pytest.raises(ReportDirectoryNotFoundError):
        _service(tmp_path / "missing-runs").list_reports()


def test_missing_report_handling(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    with pytest.raises(ReportNotFoundError):
        _service(runs_dir).get_report("gw99")


def test_invalid_report_file_handling(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "gw32"
    run_dir.mkdir(parents=True)
    (run_dir / "final_report.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(InvalidReportFileError):
        _service(runs_dir).get_report("gw32")


def test_invalid_report_schema_handling(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "gw32"
    run_dir.mkdir(parents=True)
    (run_dir / "final_report.json").write_text(
        json.dumps({"gameweek": 32}),
        encoding="utf-8",
    )

    with pytest.raises(InvalidReportFileError):
        _service(runs_dir).get_report("gw32")
