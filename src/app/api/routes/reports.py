from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.app.api.schemas.reports import ReportResponse, ReportSummary
from src.app.core.dependencies import get_report_service
from src.app.core.auth import require_admin
from src.app.domain.reports.service import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportBundle,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportService,
)
from src.app.domain.reports.suggested_team import build_suggested_team_from_reveals
from src.app.infrastructure.storage.runtime_volume import reload_runtime_volume

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[ReportSummary])
def list_reports(
    service: ReportService = Depends(get_report_service),
) -> list[ReportSummary]:
    reload_runtime_volume()
    try:
        reports = service.list_reports()
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        return []
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [_summary_response(report) for report in reports]


@router.get("/latest", response_model=ReportResponse)
def get_latest_report(
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    reload_runtime_volume()
    try:
        report = service.get_latest_report()
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="No reports found") from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")

    return _report_response(report)


@router.get("/{run_id}", response_model=ReportResponse)
def get_report(
    run_id: str,
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    reload_runtime_volume()
    try:
        report = service.get_report(run_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {run_id}") from exc
    except ReportDirectoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No reports found") from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {run_id}")

    return _report_response(report)


def _summary_response(report: Any) -> ReportSummary:
    created_at = None
    updated_at = getattr(report, "updated_at", None)
    if updated_at is not None:
        created_at = datetime.fromtimestamp(updated_at, tz=UTC).isoformat()

    return ReportSummary(
        run_id=report.run_id,
        created_at=created_at,
        title=getattr(report, "title", None),
    )


def _report_response(report: ReportBundle) -> ReportResponse:
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
    return ReportResponse(
        run_id=report.run_id,
        report=final_report.model_dump(),
    )
