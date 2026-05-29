from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PipelineRunRequest(BaseModel):
    input_data: dict[str, Any] | None = None


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str
    result: dict[str, Any] | None = None
