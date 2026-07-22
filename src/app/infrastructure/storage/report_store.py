from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from src.adapters.storage import load_json
from src.app.core.config import get_settings
from src.schemas.report_identity import ReportIdentity


FINAL_REPORT_FILENAME = "final_report.json"
AGGREGATE_REPORT_FILENAME = "aggregate_report.json"
MANIFEST_FILENAME = "manifest.json"
REPORT_INDEX_FILENAME = "index.json"


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
    season: str | None = None
    gameweek: int | None = None
    status: str = "completed"
    created_at: float | None = None

    @property
    def is_canonical(self) -> bool:
        if (
            self.status != "completed"
            or self.season in {None, "unknown"}
            or self.gameweek is None
        ):
            return False
        try:
            ReportIdentity(self.season, self.gameweek)
        except ValueError:
            return False
        return True


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
        return sorted(records, key=lambda record: (record.updated_at, record.run_id))

    def get_latest_report(
        self,
        season: str | None = None,
        gameweek: int | None = None,
    ) -> ReportRecord:
        if season is not None or gameweek is not None:
            if season is None or gameweek is None:
                raise ValueError("season and gameweek must be provided together")
            current = self.get_report_for_gameweek(season, gameweek)
            if current is not None:
                return current
        canonical = [record for record in self.list_reports() if record.is_canonical]
        if not canonical:
            raise EmptyReportDirectoryError(
                "No completed reports with a valid season and gameweek were found"
            )
        return max(canonical, key=lambda record: (record.updated_at, record.run_id))

    def get_reports_for_gameweek(
        self, season: str, gameweek: int
    ) -> list[ReportRecord]:
        identity = ReportIdentity(season, gameweek)
        return [
            record
            for record in self.list_reports()
            if record.season == identity.season and record.gameweek == identity.gameweek
        ]

    def get_report_for_gameweek(
        self, season: str, gameweek: int
    ) -> ReportRecord | None:
        completed = [
            record
            for record in self.get_reports_for_gameweek(season, gameweek)
            if record.is_canonical
        ]
        return max(
            completed,
            key=lambda record: (record.updated_at, record.run_id),
            default=None,
        )

    def get_report(self, run_id: str | Path) -> ReportRecord:
        requested = Path(run_id)
        run_dir = self._resolve_run_dir(requested)
        final_report_path = run_dir / FINAL_REPORT_FILENAME
        if not final_report_path.exists():
            raise ReportNotFoundError(
                f"Could not find final report at {final_report_path}"
            )
        return self._record_for_run_dir(run_dir)

    def get_report_by_run_id(self, run_id: str | Path) -> ReportRecord:
        return self.get_report(run_id)

    def read_json(self, path: Path) -> dict[str, Any]:
        try:
            payload = load_json(path)
        except Exception as exc:
            raise InvalidReportFileError(
                f"Could not read valid JSON report file: {path}"
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidReportFileError(
                f"Report file must contain a JSON object: {path}"
            )
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
        payload = self._read_metadata(run_dir, final_report_path)
        updated_at = self._timestamp(
            payload.get("updated_at"), final_report_path.stat().st_mtime
        )
        return ReportRecord(
            run_id=run_dir.name,
            run_dir=run_dir,
            final_report_path=final_report_path,
            aggregate_report_path=aggregate_report_path
            if aggregate_report_path.exists()
            else None,
            updated_at=updated_at,
            created_at=self._timestamp(payload.get("created_at"), updated_at),
            season=payload.get("season")
            if isinstance(payload.get("season"), str)
            else None,
            gameweek=self._valid_gameweek(payload.get("gameweek")),
            status=payload.get("status")
            if isinstance(payload.get("status"), str)
            else "completed",
        )

    def _read_metadata(self, run_dir: Path, final_report_path: Path) -> dict[str, Any]:
        manifest_path = run_dir / MANIFEST_FILENAME
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                manifest = self.read_json(manifest_path)
            except InvalidReportFileError:
                return {"status": "invalid"}
        try:
            report = self.read_json(final_report_path)
        except InvalidReportFileError:
            report = {}
        status = manifest.get("status", "completed")
        if manifest and any(
            manifest.get(field) != report.get(field) for field in ("season", "gameweek")
        ):
            status = "invalid"
        return {
            "season": manifest.get("season", report.get("season")),
            "gameweek": manifest.get("gameweek", report.get("gameweek")),
            "status": status,
            "created_at": manifest.get("created_at"),
            "updated_at": manifest.get("updated_at"),
        }

    @staticmethod
    def _valid_gameweek(gameweek: Any) -> int | None:
        if (
            isinstance(gameweek, bool)
            or not isinstance(gameweek, int)
            or not 1 <= gameweek <= 38
        ):
            return None
        return gameweek

    @staticmethod
    def _timestamp(value: Any, fallback: float) -> float:
        if not isinstance(value, str):
            return fallback
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return fallback


def update_report_index(base_dir: Path, record: ReportRecord) -> None:
    """Atomically upsert discovery metadata without copying report payloads."""
    index_path = base_dir / REPORT_INDEX_FILENAME
    entries: list[dict[str, Any]] = []
    if index_path.exists():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                entries = [item for item in loaded if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            entries = []
    relative_path = record.final_report_path.relative_to(base_dir)
    entry = {
        "run_id": record.run_id,
        "season": record.season,
        "gameweek": record.gameweek,
        "status": record.status,
        "created_at": datetime.fromtimestamp(
            record.created_at or record.updated_at, tz=UTC
        )
        .isoformat()
        .replace("+00:00", "Z"),
        "updated_at": datetime.fromtimestamp(record.updated_at, tz=UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "report_path": str(relative_path),
    }
    entries = [item for item in entries if item.get("run_id") != record.run_id]
    entries.append(entry)
    entries.sort(key=lambda item: str(item.get("run_id")))
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_suffix(f".json.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, index_path)
