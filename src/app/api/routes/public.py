from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import AfterValidator

from src.adapters.fpl import FplApiClient, FplApiError
from src.app.api.schemas.public import (
    AvailableGameweeksResponse,
    CurrentGameweekResponse,
    GameweekReportSummary,
    LatestRecommendationsResponse,
    PublicRecommendationResponse,
    SeasonGameweekIndex,
)
from src.app.core.dependencies import get_current_gameweek_service, get_report_service
from src.app.domain.reports.service import (
    EmptyReportDirectoryError,
    GameweekReportNotFoundError,
    InvalidReportFileError,
    ReportBundle,
    ReportDirectoryNotFoundError,
    ReportService,
)
from src.schemas.report_identity import validate_season
from src.app.core.public_recommendation_timing import current_timing, measure

router = APIRouter(prefix="/api", tags=["Public recommendations"])
UNAVAILABLE_DETAIL = "The latest gameweek analysis is temporarily unavailable."
SeasonQuery = Annotated[str, AfterValidator(validate_season), Query()]


def _load_latest(
    service: ReportService,
    season: str | None = None,
    gameweek: int | None = None,
) -> ReportBundle:
    try:
        return (
            service.get_public_recommendation(season, gameweek)
            if season and gameweek
            else service.get_latest_public_report()
        )
    except (
        EmptyReportDirectoryError,
        GameweekReportNotFoundError,
        ReportDirectoryNotFoundError,
    ) as exc:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL) from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc


def _last_updated(report: ReportBundle) -> str | None:
    updated_at = getattr(report, "updated_at", None)
    if updated_at is not None:
        return datetime.fromtimestamp(updated_at, tz=UTC).isoformat()
    public_value = getattr(report.final_report, "lastUpdated", None)
    if public_value:
        return str(public_value)
    return None


def _report_payload(report: ReportBundle) -> dict[str, Any]:
    return report.final_report.model_dump()


@router.get("/recommendations/latest", response_model=LatestRecommendationsResponse)
def get_latest_recommendations(
    service: ReportService = Depends(get_report_service),
    fpl: FplApiClient = Depends(get_current_gameweek_service),
) -> LatestRecommendationsResponse:
    current = None
    try:
        current = fpl.get_upcoming_gameweek()
    except FplApiError:
        pass
    report = _load_latest(
        service,
        current.season if current is not None else None,
        current.gameweek if current is not None and current.season else None,
    )
    return LatestRecommendationsResponse(
        season=report.final_report.season,
        gameweek=report.final_report.gameweek,
        last_updated_at=_last_updated(report),
        report=_report_payload(report),
    )


@router.get("/recommendations/gameweeks", response_model=AvailableGameweeksResponse)
def list_available_gameweeks(
    service: ReportService = Depends(get_report_service),
) -> AvailableGameweeksResponse:
    try:
        seasons = service.list_available_gameweeks()
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        seasons = []
    return AvailableGameweeksResponse(
        seasons=[
            SeasonGameweekIndex(
                season=season.season,
                gameweeks=[
                    GameweekReportSummary(
                        gameweek=gameweek.gameweek,
                        last_updated_at=gameweek.last_updated_at,
                        has_suggested_team=gameweek.has_suggested_team,
                    )
                    for gameweek in season.gameweeks
                ],
            )
            for season in seasons
        ]
    )


@router.get("/recommendations", response_model=PublicRecommendationResponse)
def get_recommendations(
    season: SeasonQuery,
    gameweek: Annotated[int, Query(ge=1, le=38)],
    service: ReportService = Depends(get_report_service),
) -> PublicRecommendationResponse | JSONResponse:
    timing = current_timing()
    if timing is not None:
        timing.season = season
        timing.gameweek = gameweek
    try:
        report = service.get_public_recommendation(season, gameweek)
    except GameweekReportNotFoundError:
        if timing is not None and timing.failure_stage is None:
            timing.mark_failure("recommendation_lookup", category="report_not_found")
        return _not_found_response(season, gameweek)
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        if timing is not None:
            timing.mark_failure("recommendation_lookup", category="report_not_found")
        return _not_found_response(season, gameweek)
    except InvalidReportFileError as exc:
        if timing is not None:
            timing.mark_failure(
                "final_report_validation", exc, category="invalid_stored_report"
            )
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc
    if timing is not None:
        timing.run_id = report.run_id
    with measure("response_model_ms", "response_model_construction"):
        response_model = PublicRecommendationResponse(
            season=report.final_report.season,
            gameweek=report.final_report.gameweek,
            last_updated_at=_last_updated(report),
            report=_report_payload(report),
        )
    with measure("serialization_ms", "response_serialization"):
        return JSONResponse(content=response_model.model_dump(mode="json"))


def _not_found_response(season: str, gameweek: int) -> JSONResponse:
    content = {
        "error": {
            "code": "REPORT_NOT_FOUND",
            "message": (
                "No completed report is available for season "
                f"{season}, gameweek {gameweek}."
            ),
            "details": {"season": season, "gameweek": gameweek},
        }
    }
    with measure("serialization_ms", "response_serialization"):
        return JSONResponse(status_code=404, content=content)


@router.get("/gameweek/current", response_model=CurrentGameweekResponse)
def get_current_gameweek(
    service: ReportService = Depends(get_report_service),
    fpl: FplApiClient = Depends(get_current_gameweek_service),
) -> CurrentGameweekResponse:
    try:
        current = fpl.get_upcoming_gameweek()
    except FplApiError as exc:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc
    if current is None:
        return CurrentGameweekResponse(recommendations_available=False)

    try:
        report = _load_latest(service, current.season, current.gameweek)
    except HTTPException as exc:
        if exc.status_code == 404:
            return CurrentGameweekResponse(
                gameweek=current.gameweek,
                deadline=current.deadline,
                recommendations_available=False,
            )
        raise
    report_is_current = report.final_report.gameweek == current.gameweek and (
        current.season is None or report.final_report.season == current.season
    )
    return CurrentGameweekResponse(
        gameweek=current.gameweek,
        deadline=current.deadline,
        last_updated_at=_last_updated(report),
        recommendations_available=report_is_current,
    )
