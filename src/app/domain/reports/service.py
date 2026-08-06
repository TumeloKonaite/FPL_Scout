from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime

from pydantic import ValidationError

from src.app.domain.reports.suggested_team import validate_consensus_squad
from src.app.infrastructure.models import CompletedReportRun
from src.app.infrastructure.report_repository import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    PublicRecommendationRecord,
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

    def get_reports_for_gameweek(
        self, season: str, gameweek: int
    ) -> list[ReportSummary]:
        return [
            self._summary(row)
            for row in self.repository.completed_for_gameweek(season, gameweek)
        ]

    def list_available_gameweeks(self) -> list[SeasonGameweekSummary]:
        rows = self.repository.list_reports(completed_only=True)
        newest: dict[tuple[str, int], CompletedReportRun] = {}
        for row in rows:
            newest[(row.season, row.gameweek)] = row
        grouped: dict[str, list[GameweekReportSummary]] = {}
        for (season, gameweek), row in sorted(newest.items(), reverse=True):
            try:
                bundle = self._bundle(row)
            except InvalidReportFileError:
                continue
            grouped.setdefault(season, []).append(
                GameweekReportSummary(
                    gameweek=gameweek,
                    last_updated_at=row.updated_at,
                    has_suggested_team=(
                        bundle.final_report.suggested_team is not None
                        and validate_consensus_squad(bundle.final_report.suggested_team)
                    ),
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
            final_snapshot = deepcopy(row.final_report)
            if not isinstance(final_snapshot, dict):
                raise TypeError("final_report must be a JSON object")
            suggested = final_snapshot.get("suggested_team")
            if isinstance(suggested, dict) and "constructionMethod" not in suggested:
                has_lineup = bool(
                    suggested.get("startingXi")
                    or suggested.get("starters")
                    or suggested.get("players")
                )
                suggested["constructionMethod"] = (
                    "legacy_snapshot" if has_lineup else "insufficient_evidence"
                )
                suggested["consensusStrength"] = "insufficient"
                suggested["provenanceAvailable"] = False
                suggested["provenance"] = None
                if has_lineup:
                    # This is a display-compatibility outcome only; it is not
                    # evidence that the historical lineup was a consensus.
                    suggested["constructionStatus"] = "consensus"
            return FinalGameweekReport.model_validate(final_snapshot)
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
