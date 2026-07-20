from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.adapters.storage import load_json
from src.app.core.config import get_settings


FINAL_REPORT_FILENAME = "final_report.json"
AGGREGATE_REPORT_FILENAME = "aggregate_report.json"


class ReportStoreError(Exception):
    """Base error for report storage failures."""


class ReportDirectoryNotFoundError(ReportStoreError, FileNotFoundError):
    """Raised when the configured reports directory is missing."""


class EmptyReportDirectoryError(ReportStoreError, FileNotFoundError):
    """Raised when no readable report run folders exist."""


class ReportNotFoundError(ReportStoreError, FileNotFoundError):
    """Raised when a requested run cannot be found."""


class InvalidReportFileError(ReportStoreError, ValueError):
    """Raised when a report artifact cannot be read as a valid report file."""


@dataclass(frozen=True)
class ReportRecord:
    run_id: str
    run_dir: Path
    final_report_path: Path
    aggregate_report_path: Path | None
    updated_at: float
    gameweek: int | None = None


class ReportStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or get_settings().REPORTS_DIR)

    def list_reports(self) -> list[ReportRecord]:
        if not self.base_dir.exists():
            raise ReportDirectoryNotFoundError(
                f"Reports directory does not exist: {self.base_dir}"
            )
        if not self.base_dir.is_dir():
            raise ReportDirectoryNotFoundError(
                f"Reports path is not a directory: {self.base_dir}"
            )

        records = [
            self._record_for_run_dir(path)
            for path in self.base_dir.iterdir()
            if path.is_dir() and (path / FINAL_REPORT_FILENAME).exists()
        ]
        if not records:
            raise EmptyReportDirectoryError(
                f"No run folders containing {FINAL_REPORT_FILENAME} were found in {self.base_dir}"
            )
        return sorted(
            records,
            key=lambda record: (
                record.gameweek is not None,
                record.gameweek if record.gameweek is not None else -1,
                record.updated_at,
                record.run_id,
            ),
        )

    def get_latest_report(self) -> ReportRecord:
        return self.list_reports()[-1]

    def get_report(self, run_id: str | Path) -> ReportRecord:
        requested = Path(run_id)
        run_dir = self._resolve_run_dir(requested)
        final_report_path = run_dir / FINAL_REPORT_FILENAME
        if not final_report_path.exists():
            raise ReportNotFoundError(f"Could not find final report at {final_report_path}")
        return self._record_for_run_dir(run_dir)

    def read_json(self, path: Path) -> dict[str, Any]:
        try:
            payload = load_json(path)
        except Exception as exc:
            raise InvalidReportFileError(f"Could not read valid JSON report file: {path}") from exc
        if not isinstance(payload, dict):
            raise InvalidReportFileError(f"Report file must contain a JSON object: {path}")
        return payload

    def _resolve_run_dir(self, requested: Path) -> Path:
        if requested.is_dir():
            return requested
        if requested.name == FINAL_REPORT_FILENAME:
            return requested.parent
        if requested.is_absolute() or len(requested.parts) > 1:
            return requested
        return self.base_dir / requested

    def _record_for_run_dir(self, run_dir: Path) -> ReportRecord:
        final_report_path = run_dir / FINAL_REPORT_FILENAME
        aggregate_report_path = run_dir / AGGREGATE_REPORT_FILENAME
        return ReportRecord(
            run_id=run_dir.name,
            run_dir=run_dir,
            final_report_path=final_report_path,
            aggregate_report_path=aggregate_report_path if aggregate_report_path.exists() else None,
            updated_at=final_report_path.stat().st_mtime,
            gameweek=self._read_gameweek(final_report_path),
        )

    def _read_gameweek(self, final_report_path: Path) -> int | None:
        try:
            gameweek = self.read_json(final_report_path).get("gameweek")
        except InvalidReportFileError:
            return None
        if isinstance(gameweek, bool) or not isinstance(gameweek, int):
            return None
        return gameweek if gameweek > 0 else None
