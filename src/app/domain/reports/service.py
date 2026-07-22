from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
    updated_at: float


@dataclass(frozen=True)
class GameweekReportSummary:
    gameweek: int
    last_updated_at: datetime
    has_suggested_team: bool


@dataclass(frozen=True)
class SeasonGameweekSummary:
    season: str
    gameweeks: list[GameweekReportSummary]


class GameweekReportNotFoundError(LookupError):
    def __init__(self, season: str, gameweek: int) -> None:
        self.season = season
        self.gameweek = gameweek
        super().__init__(
            f"No completed report is available for season {season}, "
            f"gameweek {gameweek}."
        )


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
        if (season is None) != (gameweek is None):
            raise ValueError("season and gameweek must be provided together")
        if season is not None and gameweek is not None:
            try:
                return self.get_report_for_gameweek(season, gameweek)
            except GameweekReportNotFoundError:
                pass
        candidates = [
            record for record in self.store.list_reports() if record.is_canonical
        ]
        if candidates:
            return self._newest_valid_bundle(candidates)
        # Keep compatibility with storage implementations that hydrate identity
        # only when the report body is loaded. The filesystem store itself still
        # rejects non-canonical public reports in get_latest_report().
        return self._load_record(self.store.get_latest_report())

    def get_report_for_gameweek(
        self, season: str, gameweek: int
    ) -> ReportBundle:
        try:
            candidates = [
                record
                for record in self.store.get_reports_for_gameweek(season, gameweek)
                if record.is_canonical
            ]
            return self._newest_valid_bundle(candidates)
        except (EmptyReportDirectoryError, ReportDirectoryNotFoundError) as exc:
            raise GameweekReportNotFoundError(season, gameweek) from exc

    def list_available_gameweeks(self) -> list[SeasonGameweekSummary]:
        records = self.store.list_reports()
        identities = sorted(
            {
                (record.season, record.gameweek)
                for record in records
                if record.is_canonical
            },
            reverse=True,
        )
        grouped: dict[str, list[GameweekReportSummary]] = {}
        for season, gameweek in identities:
            candidates = [
                record
                for record in records
                if record.is_canonical
                and record.season == season
                and record.gameweek == gameweek
            ]
            try:
                bundle = self._newest_valid_bundle(candidates)
            except EmptyReportDirectoryError:
                continue
            grouped.setdefault(season, []).append(
                GameweekReportSummary(
                    gameweek=gameweek,
                    last_updated_at=datetime.fromtimestamp(bundle.updated_at, tz=UTC),
                    has_suggested_team=bundle.final_report.suggested_team is not None,
                )
            )
        return [
            SeasonGameweekSummary(
                season=season,
                gameweeks=sorted(
                    gameweeks, key=lambda summary: summary.gameweek, reverse=True
                ),
            )
            for season, gameweeks in sorted(grouped.items(), reverse=True)
        ]

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
            updated_at=record.updated_at,
        )

    def _newest_valid_bundle(
        self, candidates: list[ReportRecord]
    ) -> ReportBundle:
        for record in sorted(
            candidates,
            key=lambda candidate: (candidate.updated_at, candidate.run_id),
            reverse=True,
        ):
            try:
                return self._load_record(record)
            except InvalidReportFileError:
                continue
        raise EmptyReportDirectoryError("No valid completed reports were found")

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
    "GameweekReportNotFoundError",
    "GameweekReportSummary",
    "InvalidReportFileError",
    "ReportBundle",
    "ReportDirectoryNotFoundError",
    "ReportNotFoundError",
    "ReportService",
    "ReportSummary",
    "SeasonGameweekSummary",
]
