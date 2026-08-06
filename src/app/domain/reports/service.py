from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

from src.app.infrastructure.models import CompletedReportRun
from src.app.domain.reports.index_metadata import normalize_legacy_final_report
from src.app.infrastructure.report_repository import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    PublicRecommendationRecord,
    PublicRecommendationMetadata,
    ReportRepository,
)
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.app.core.public_recommendation_timing import current_timing, measure


@dataclass(frozen=True)
class ReportSummary:
    run_id: str
    season: str
    gameweek: int
    updated_at: float
    status: str


@dataclass(frozen=True)
class ReportBundle:
    run_id: str
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
            f"No completed report is available for season {season}, gameweek {gameweek}."
        )


class ReportService:
    def __init__(self, repository: ReportRepository | None = None) -> None:
        self.repository = repository or ReportRepository()

    def list_reports(self) -> list[ReportSummary]:
        return [self._summary(row) for row in self.repository.list_reports()]

    def get_latest_report(
        self, season: str | None = None, gameweek: int | None = None
    ) -> ReportBundle:
        return self._bundle(self.repository.latest_completed(season, gameweek))

    def get_latest_public_report(self) -> ReportBundle:
        return self._bundle(self.repository.latest_published())

    def get_report_for_gameweek(self, season: str, gameweek: int) -> ReportBundle:
        """Compatibility alias for the public recommendation retrieval path."""
        return self.get_public_recommendation(season, gameweek)

    def get_public_recommendation(self, season: str, gameweek: int) -> ReportBundle:
        row = self.repository.latest_public_recommendation(season, gameweek)
        if row is None:
            timing = current_timing()
            if timing is not None:
                timing.mark_failure("db_result_processing", category="report_not_found")
            raise GameweekReportNotFoundError(season, gameweek)
        timing = current_timing()
        if timing is not None:
            # The row has been selected even if its stored payload later fails
            # validation, so the run identifier remains useful failure context.
            timing.run_id = row.run_id
        try:
            with measure("validation_ms", "final_report_validation"):
                final = self._validate_final_report(row)
        except InvalidReportFileError as exc:
            timing = current_timing()
            if timing is not None:
                timing.mark_failure(
                    "final_report_validation",
                    exc,
                    category="invalid_stored_report",
                )
            raise GameweekReportNotFoundError(season, gameweek) from exc
        return ReportBundle(
            run_id=row.run_id,
            final_report=final,
            aggregate_report=None,
            updated_at=row.updated_at.timestamp(),
        )

    def get_public_recommendation_metadata(
        self, season: str, gameweek: int
    ) -> PublicRecommendationMetadata:
        row = self.repository.public_recommendation_metadata(season, gameweek)
        if row is None:
            raise GameweekReportNotFoundError(season, gameweek)
        return row

    def get_public_recommendation_version(
        self, season: str, gameweek: int, run_id: str
    ) -> ReportBundle:
        row = self.repository.public_recommendation_by_run_id(
            season, gameweek, run_id
        )
        if row is None:
            raise GameweekReportNotFoundError(season, gameweek)
        timing = current_timing()
        if timing is not None:
            timing.run_id = row.run_id
        try:
            with measure("validation_ms", "final_report_validation"):
                final = self._validate_final_report(row)
        except InvalidReportFileError as exc:
            if timing is not None:
                timing.mark_failure(
                    "final_report_validation",
                    exc,
                    category="invalid_stored_report",
                )
            raise GameweekReportNotFoundError(season, gameweek) from exc
        return ReportBundle(
            run_id=row.run_id,
            final_report=final,
            aggregate_report=None,
            updated_at=row.updated_at.timestamp(),
        )

    def get_reports_for_gameweek(
        self, season: str, gameweek: int
    ) -> list[ReportSummary]:
        return [
            self._summary(row)
            for row in self.repository.completed_for_gameweek(season, gameweek)
        ]

    def list_available_gameweeks(self) -> list[SeasonGameweekSummary]:
        rows = self.repository.public_gameweek_index()
        grouped: dict[str, list[GameweekReportSummary]] = {}
        for row in rows:
            grouped.setdefault(row.season, []).append(
                GameweekReportSummary(
                    gameweek=row.gameweek,
                    last_updated_at=row.updated_at,
                    has_suggested_team=row.has_suggested_team,
                )
            )
        return [
            SeasonGameweekSummary(
                season=season,
                gameweeks=sorted(items, key=lambda item: item.gameweek, reverse=True),
            )
            for season, items in sorted(grouped.items(), reverse=True)
        ]

    def get_report(self, run_id: str) -> ReportBundle:
        """Load a report by ID for authenticated administrative inspection."""
        row = self.repository.get(run_id)
        return self._bundle(row)

    @staticmethod
    def _summary(row: CompletedReportRun) -> ReportSummary:
        return ReportSummary(
            run_id=row.run_id,
            season=row.season,
            gameweek=row.gameweek,
            updated_at=row.updated_at.timestamp(),
            status=row.status,
        )

    @staticmethod
    def _validate_final_report(
        row: CompletedReportRun | PublicRecommendationRecord,
    ) -> FinalGameweekReport:
        try:
            return FinalGameweekReport.model_validate(
                normalize_legacy_final_report(row.final_report)
            )
        except (TypeError, ValidationError) as exc:
            raise InvalidReportFileError(
                f"Invalid report snapshot: {row.run_id}"
            ) from exc

    @staticmethod
    def _bundle(row: CompletedReportRun) -> ReportBundle:
        final = ReportService._validate_final_report(row)
        try:
            aggregate = AggregatedFPLReport.model_validate(row.aggregate_report)
        except ValidationError as exc:
            raise InvalidReportFileError(
                f"Invalid report snapshot: {row.run_id}"
            ) from exc
        return ReportBundle(
            run_id=row.run_id,
            final_report=final,
            aggregate_report=aggregate,
            updated_at=row.updated_at.timestamp(),
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
