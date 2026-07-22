from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from src.app.infrastructure.storage.report_store import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportRecord,
    ReportStore,
)
from src.app.domain.reports.suggested_team import (
    build_explicit_position_catalog,
    build_suggested_team_from_reveals,
)
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport


@dataclass(frozen=True)
class ReportSummary:
    run_id: str
    season: str | None
    gameweek: int | None
    run_dir: Path
    final_report_path: Path
    aggregate_report_path: Path | None
    updated_at: float
    status: str


@dataclass(frozen=True)
class ReportBundle:
    run_id: str
    run_dir: Path
    final_report_path: Path
    aggregate_report_path: Path | None
    final_report: FinalGameweekReport
    aggregate_report: AggregatedFPLReport | None


class ReportService:
    def __init__(self, store: ReportStore | None = None) -> None:
        self.store = store or ReportStore()

    def list_reports(self) -> list[ReportSummary]:
        return [
            self._summary_from_record(record) for record in self.store.list_reports()
        ]

    def get_latest_report(
        self,
        season: str | None = None,
        gameweek: int | None = None,
    ) -> ReportBundle:
        record = (
            self.store.get_latest_report(season, gameweek)
            if season is not None or gameweek is not None
            else self.store.get_latest_report()
        )
        return self._load_record(record)

    def get_report_for_gameweek(
        self, season: str, gameweek: int
    ) -> ReportBundle | None:
        record = self.store.get_report_for_gameweek(season, gameweek)
        return self._load_record(record) if record is not None else None

    def get_reports_for_gameweek(
        self, season: str, gameweek: int
    ) -> list[ReportSummary]:
        return [
            self._summary_from_record(record)
            for record in self.store.get_reports_for_gameweek(season, gameweek)
        ]

    def get_report(self, run_id: str | Path) -> ReportBundle:
        return self._load_record(self.store.get_report(run_id))

    def _load_record(self, record: ReportRecord) -> ReportBundle:
        final_report = self._load_final_report(record)
        aggregate_report = self._load_aggregate_report(record)
        if final_report.suggested_team is None and aggregate_report is not None:
            final_report = final_report.model_copy(
                update={
                    "suggested_team": build_suggested_team_from_reveals(
                        aggregate_report.expert_team_reveals,
                        self._build_position_catalog(),
                    )
                }
            )
        return ReportBundle(
            run_id=record.run_id,
            run_dir=record.run_dir,
            final_report_path=record.final_report_path,
            aggregate_report_path=record.aggregate_report_path,
            final_report=final_report,
            aggregate_report=aggregate_report,
        )

    def _build_position_catalog(self) -> dict[str, str]:
        catalog: dict[str, str] = {}
        conflicts: set[str] = set()
        for record in self.store.list_reports():
            try:
                aggregate = self._load_aggregate_report(record)
            except InvalidReportFileError:
                continue
            if aggregate is None:
                continue
            for name, position in build_explicit_position_catalog(
                aggregate.expert_team_reveals
            ).items():
                if name in catalog and catalog[name] != position:
                    conflicts.add(name)
                else:
                    catalog[name] = position
        for name in conflicts:
            catalog.pop(name, None)
        return catalog

    def _load_final_report(self, record: ReportRecord) -> FinalGameweekReport:
        try:
            return FinalGameweekReport.model_validate(
                self.store.read_json(record.final_report_path)
            )
        except ValidationError as exc:
            raise InvalidReportFileError(
                f"Invalid final report file: {record.final_report_path}"
            ) from exc

    def _load_aggregate_report(
        self, record: ReportRecord
    ) -> AggregatedFPLReport | None:
        if record.aggregate_report_path is None:
            return None
        try:
            return AggregatedFPLReport.model_validate(
                self.store.read_json(record.aggregate_report_path)
            )
        except ValidationError as exc:
            raise InvalidReportFileError(
                f"Invalid aggregate report file: {record.aggregate_report_path}"
            ) from exc

    @staticmethod
    def _summary_from_record(record: ReportRecord) -> ReportSummary:
        return ReportSummary(
            run_id=record.run_id,
            season=record.season,
            gameweek=record.gameweek,
            run_dir=record.run_dir,
            final_report_path=record.final_report_path,
            aggregate_report_path=record.aggregate_report_path,
            updated_at=record.updated_at,
            status=record.status,
        )


__all__ = [
    "EmptyReportDirectoryError",
    "InvalidReportFileError",
    "ReportBundle",
    "ReportDirectoryNotFoundError",
    "ReportNotFoundError",
    "ReportService",
    "ReportSummary",
]
