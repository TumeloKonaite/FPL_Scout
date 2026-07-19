from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class PipelineRunRequest(BaseModel):
    input_data: dict[str, Any] | None = None


class PipelineRunResponse(BaseModel):
    run_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
