from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.app.domain.reports.service import ReportService
from src.app.infrastructure.storage.report_store import (
    InvalidReportFileError,
    ReportRecord,
)


def _final_report_payload(gameweek: int = 32) -> dict[str, Any]:
    return {
        "gameweek": gameweek,
        "overview": "Clean overview",
        "transfers": [],
        "captaincy": [],
        "chip_strategy": [],
        "fixture_notes": [],
        "disagreements": [],
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
        "conclusion": "Clean conclusion",
    }


@dataclass
class StubReportStore:
    records: list[ReportRecord]
    payloads: dict[Path, dict[str, Any]]

    def list_reports(self) -> list[ReportRecord]:
        return self.records

    def get_latest_report(self) -> ReportRecord:
        return self.records[-1]

    def get_report(self, run_id: str | Path) -> ReportRecord:
        return next(record for record in self.records if record.run_id == str(run_id))

    def read_json(self, path: Path) -> dict[str, Any]:
        return self.payloads[path]


def _record(run_id: str, tmp_path: Path, updated_at: float = 1.0) -> ReportRecord:
    run_dir = tmp_path / run_id
    return ReportRecord(
        run_id=run_id,
        run_dir=run_dir,
        final_report_path=run_dir / "final_report.json",
        aggregate_report_path=None,
        updated_at=updated_at,
    )


def test_report_service_lists_summaries_without_loading_report_bodies(tmp_path) -> None:
    record = _record("gw32", tmp_path, updated_at=123.0)
    service = ReportService(StubReportStore([record], {}))

    summaries = service.list_reports()

    assert len(summaries) == 1
    assert summaries[0].run_id == "gw32"
    assert summaries[0].final_report_path == record.final_report_path
    assert summaries[0].updated_at == 123.0


def test_report_service_loads_and_validates_latest_final_report(tmp_path) -> None:
    record = _record("gw32", tmp_path)
    service = ReportService(
        StubReportStore([record], {record.final_report_path: _final_report_payload(32)})
    )

    bundle = service.get_latest_report()

    assert bundle.run_id == "gw32"
    assert bundle.final_report.gameweek == 32
    assert bundle.final_report.overview == "Clean overview"
    assert bundle.aggregate_report is None


def test_report_service_wraps_invalid_final_report_schema(tmp_path) -> None:
    record = _record("gw32", tmp_path)
    service = ReportService(StubReportStore([record], {record.final_report_path: {}}))

    with pytest.raises(InvalidReportFileError, match="Invalid final report file"):
        service.get_report("gw32")
