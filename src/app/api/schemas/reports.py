from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReportSummary(BaseModel):
    run_id: str
    created_at: str | None = None
    title: str | None = None


class ReportResponse(BaseModel):
    run_id: str
    report: dict[str, Any]
