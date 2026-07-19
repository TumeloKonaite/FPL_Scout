from __future__ import annotations

from hmac import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from src.app.api.schemas.pipeline_runs import PipelineRunRequest, PipelineRunResponse
from src.app.core.config import get_settings
from src.app.domain.pipeline.service import create_pipeline_run, get_pipeline_status

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])


async def require_pipeline_token(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.PIPELINE_API_TOKEN
    if not expected:
        if settings.ENVIRONMENT.casefold() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pipeline mutation authentication is not configured",
            )
        return
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not supplied or not compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid pipeline bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline_run(
    request: PipelineRunRequest,
    response: Response,
    _: None = Depends(require_pipeline_token),
) -> PipelineRunResponse:
    try:
        result = create_pipeline_run(input_data=request.input_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
