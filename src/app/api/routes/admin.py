from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.app.api.routes.reports import _report_response, _summary_response
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
    ReportDirectoryNotFoundError,
    ReportNotFoundError,
    ReportService,
)
from src.app.infrastructure.storage.pipeline_run_store import (
    ActivePipelineRunError,
    PipelineRunStore,
)
from src.app.infrastructure.storage.runtime_volume import reload_runtime_volume

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


def _start(request: PipelineRunRequest, response: Response) -> PipelineRunResponse:
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


@router.post("/pipeline/run", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_pipeline(request: PipelineRunRequest, response: Response) -> PipelineRunResponse:
    return _start(request, response)


@router.post("/reports/generate", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_report(request: PipelineRunRequest, response: Response) -> PipelineRunResponse:
    return _start(request, response)


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
def pipeline_status() -> PipelineStatusResponse:
    reload_runtime_volume()
    latest = PipelineRunStore().get_latest()
    if latest is None:
        return PipelineStatusResponse(status="idle", latest_run=None)
    run = PipelineRunResponse.model_validate(latest)
    return PipelineStatusResponse(status=run.status, latest_run=run)


@router.get("/runs/latest", response_model=PipelineRunResponse)
def latest_run() -> PipelineRunResponse:
    reload_runtime_volume()
    latest = PipelineRunStore().get_latest()
    if latest is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return PipelineRunResponse.model_validate(latest)


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
def pipeline_run(run_id: str) -> PipelineRunResponse:
    result = get_pipeline_status(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return PipelineRunResponse.model_validate(result)


@router.get("/reports", response_model=list[ReportSummary])
def reports(service: ReportService = Depends(get_report_service)) -> list[ReportSummary]:
    reload_runtime_volume()
    try:
        return [_summary_response(report) for report in service.list_reports()]
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        return []
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/reports/{run_id}", response_model=ReportResponse)
def report(run_id: str, service: ReportService = Depends(get_report_service)) -> ReportResponse:
    reload_runtime_volume()
    try:
        return _report_response(service.get_report(run_id))
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {run_id}") from exc
    except (ReportDirectoryNotFoundError, EmptyReportDirectoryError) as exc:
        raise HTTPException(status_code=404, detail="No reports found") from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
