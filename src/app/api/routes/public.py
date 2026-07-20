from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.app.api.schemas.public import CurrentGameweekResponse, LatestRecommendationsResponse
from src.app.core.dependencies import get_report_service
from src.app.domain.reports.service import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportBundle,
    ReportDirectoryNotFoundError,
    ReportService,
)
from src.app.domain.reports.suggested_team import build_suggested_team_from_reveals
from src.app.infrastructure.storage.runtime_volume import reload_runtime_volume

router = APIRouter(prefix="/api", tags=["Public recommendations"])
UNAVAILABLE_DETAIL = "The latest gameweek analysis is temporarily unavailable."


def _load_latest(service: ReportService) -> ReportBundle:
    reload_runtime_volume()
    try:
        return service.get_latest_report()
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL) from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc


def _last_updated(report: ReportBundle) -> str | None:
    public_value = getattr(report.final_report, "lastUpdated", None)
    if public_value:
        return str(public_value)
    path = getattr(report, "final_report_path", None)
    if path is not None:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    return None


def _report_payload(report: ReportBundle) -> dict[str, Any]:
    final_report = report.final_report
    aggregate_report = getattr(report, "aggregate_report", None)
    if final_report.suggested_team is None and aggregate_report is not None:
        final_report = final_report.model_copy(
            update={
                "suggested_team": build_suggested_team_from_reveals(
                    aggregate_report.expert_team_reveals
                )
            }
        )
    return final_report.model_dump()


@router.get("/recommendations/latest", response_model=LatestRecommendationsResponse)
def get_latest_recommendations(
    service: ReportService = Depends(get_report_service),
) -> LatestRecommendationsResponse:
    report = _load_latest(service)
    return LatestRecommendationsResponse(
        gameweek=report.final_report.gameweek,
        last_updated_at=_last_updated(report),
        report=_report_payload(report),
    )


@router.get("/gameweek/current", response_model=CurrentGameweekResponse)
def get_current_gameweek(
    service: ReportService = Depends(get_report_service),
) -> CurrentGameweekResponse:
    try:
        report = _load_latest(service)
    except HTTPException as exc:
        if exc.status_code == 404:
            return CurrentGameweekResponse(recommendations_available=False)
        raise
    return CurrentGameweekResponse(
        gameweek=report.final_report.gameweek,
        deadline=str(report.final_report.deadline) if report.final_report.deadline else None,
        last_updated_at=_last_updated(report),
        recommendations_available=True,
    )
