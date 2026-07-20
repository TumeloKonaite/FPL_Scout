from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.app.api.schemas.pipeline_runs import PipelineRunRequest, PipelineRunResponse
from src.app.core.auth import require_admin
from src.app.domain.pipeline.service import create_pipeline_run, get_pipeline_status
from src.app.infrastructure.storage.pipeline_run_store import ActivePipelineRunError

router = APIRouter(
    prefix="/api/pipeline-runs",
    tags=["pipeline-runs"],
    dependencies=[Depends(require_admin)],
)


@router.post("", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline_run(
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

    response.headers["Location"] = f"/api/pipeline-runs/{result['run_id']}"
    return PipelineRunResponse.model_validate(result)


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: str) -> PipelineRunResponse:
    result = get_pipeline_status(run_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse.model_validate(result)
