from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.app.api.schemas.pipeline_runs import PipelineRunRequest, PipelineRunResponse
from src.app.domain.pipeline.service import get_pipeline_status, run_pipeline

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])


@router.post("", response_model=PipelineRunResponse)
def create_pipeline_run(request: PipelineRunRequest) -> PipelineRunResponse:
    result = run_pipeline(input_data=request.input_data)

    return PipelineRunResponse(
        run_id=result["run_id"],
        status=result["status"],
        result=result.get("result"),
    )


@router.get("/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(run_id: str) -> PipelineRunResponse:
    result = get_pipeline_status(run_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse(
        run_id=result["run_id"],
        status=result["status"],
        result=result.get("result"),
    )
