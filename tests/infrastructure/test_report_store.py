from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.app.core.config import get_settings
from src.app.infrastructure.storage.report_store import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportStore,
)


def _write_final_report(run_dir: Path, payload: dict | str | list) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "final_report.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_report_store_uses_configured_reports_dir(monkeypatch, tmp_path) -> None:
    reports_dir = tmp_path / "configured" / "reports"
    monkeypatch.setenv("REPORTS_DIR", str(reports_dir))
    get_settings.cache_clear()

    try:
        store = ReportStore()
        assert store.base_dir == reports_dir
    finally:
        get_settings.cache_clear()


def test_report_store_lists_run_directories_with_final_reports(tmp_path) -> None:
    base_dir = tmp_path / "reports"
    older = _write_final_report(base_dir / "gw31", {"gameweek": 31})
    newer = _write_final_report(base_dir / "gw32", {"gameweek": 32})
    (base_dir / "scratch").mkdir()
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_100, 1_700_000_100))

    records = ReportStore(base_dir).list_reports()

    assert [record.run_id for record in records] == ["gw31", "gw32"]
    assert ReportStore(base_dir).get_latest_report().run_id == "gw32"


def test_report_store_resolves_run_id_directory_and_report_file_paths(tmp_path) -> None:
    base_dir = tmp_path / "reports"
    final_report = _write_final_report(base_dir / "gw32", {"gameweek": 32})
    store = ReportStore(base_dir)

    assert store.get_report("gw32").run_dir == base_dir / "gw32"
    assert store.get_report(base_dir / "gw32").run_id == "gw32"
    assert store.get_report(final_report).final_report_path == final_report


def test_report_store_raises_for_missing_reports_directory(tmp_path) -> None:
    with pytest.raises(ReportDirectoryNotFoundError):
        ReportStore(tmp_path / "missing").list_reports()


def test_report_store_raises_for_empty_reports_directory(tmp_path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    with pytest.raises(EmptyReportDirectoryError):
        ReportStore(reports_dir).list_reports()


def test_report_store_raises_for_missing_report_file(tmp_path) -> None:
    reports_dir = tmp_path / "reports"
    (reports_dir / "gw32").mkdir(parents=True)

    with pytest.raises(ReportNotFoundError):
        ReportStore(reports_dir).get_report("gw32")


def test_report_store_wraps_corrupt_json_files(tmp_path) -> None:
    final_report = _write_final_report(tmp_path / "reports" / "gw32", "{not-json")

    with pytest.raises(InvalidReportFileError):
        ReportStore(tmp_path / "reports").read_json(final_report)


def test_report_store_rejects_non_object_json_report_files(tmp_path) -> None:
    final_report = _write_final_report(tmp_path / "reports" / "gw32", [])

    with pytest.raises(InvalidReportFileError, match="JSON object"):
        ReportStore(tmp_path / "reports").read_json(final_report)
