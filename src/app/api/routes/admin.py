from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.app.api.schemas.pipeline_runs import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
)
from src.app.api.schemas.reports import ReportResponse, ReportSummary
from src.app.core.auth import require_admin
from src.app.core.dependencies import get_report_service
from src.app.domain.pipeline.service import create_pipeline_run, get_pipeline_status
from src.app.domain.reports.service import (
    EmptyReportDirectoryError,
    InvalidReportFileError,
    ReportBundle,
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportService,
)
from src.app.infrastructure.pipeline_run_repository import (
    ActivePipelineRunError,
    InvalidPipelineRunTransition,
    PipelineRunRepository,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "/pipeline/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start the report pipeline",
    description=(
        "Queues the complete analysis and report-generation pipeline and returns "
        "the durable run record."
    ),
)
def start_pipeline(
    request: PipelineRunRequest,
    response: Response,
) -> PipelineRunResponse:
    try:
        result = create_pipeline_run(input_data=request.input_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ActivePipelineRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Pipeline worker could not be started") from exc
    response.headers["Location"] = f"/api/admin/runs/{result['run_id']}"
    return PipelineRunResponse.model_validate(result)


@router.get(
    "/pipeline/status",
    response_model=PipelineStatusResponse,
    summary="Get pipeline status",
    description="Returns the latest durable run, or an idle status when none exists.",
)
def pipeline_status() -> PipelineStatusResponse:
    latest = get_pipeline_status()
    if latest is None:
        return PipelineStatusResponse(status="idle", latest_run=None)
    run = PipelineRunResponse.model_validate(latest)
    return PipelineStatusResponse(status=run.status, latest_run=run)


@router.get(
    "/runs/{run_id}",
    response_model=PipelineRunResponse,
    summary="Get a pipeline run",
    description="Returns one durable pipeline run by its identifier.",
)
def pipeline_run(run_id: str) -> PipelineRunResponse:
    result = get_pipeline_status(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return PipelineRunResponse.model_validate(result)


@router.post(
    "/runs/{run_id}/fail",
    response_model=PipelineRunResponse,
    summary="Fail a stuck pipeline run",
)
def fail_pipeline_run(run_id: str) -> PipelineRunResponse:
    try:
        result = PipelineRunRepository().fail_active(
            run_id, "Pipeline run was stopped by an administrator."
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pipeline run not found") from exc
    except InvalidPipelineRunTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PipelineRunResponse.model_validate(result)


@router.get(
    "/reports",
    response_model=list[ReportSummary],
    summary="List internal reports",
    description="Lists completed report records, including internal run identifiers.",
)
def reports(service: ReportService = Depends(get_report_service)) -> list[ReportSummary]:
    try:
        return [_summary_response(report) for report in service.list_reports()]
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        return []
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/reports/{run_id}",
    response_model=ReportResponse,
    summary="Get an internal report",
    description="Returns one completed report by its internal pipeline run identifier.",
)
def report(run_id: str, service: ReportService = Depends(get_report_service)) -> ReportResponse:
    try:
        return _report_response(service.get_report(run_id))
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {run_id}") from exc
    except (ReportDirectoryNotFoundError, EmptyReportDirectoryError) as exc:
        raise HTTPException(status_code=404, detail="No reports found") from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _summary_response(report: Any) -> ReportSummary:
    created_at = None
    updated_at = getattr(report, "updated_at", None)
    if updated_at is not None:
        created_at = datetime.fromtimestamp(updated_at, tz=UTC).isoformat()

    return ReportSummary(
        run_id=report.run_id,
        season=getattr(report, "season", None),
        gameweek=getattr(report, "gameweek", None),
        created_at=created_at,
        title=getattr(report, "title", None),
    )


def _report_response(report: ReportBundle) -> ReportResponse:
    return ReportResponse(
        run_id=report.run_id,
        report=report.final_report.model_dump(),
    )
