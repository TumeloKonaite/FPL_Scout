from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from src.app.core.config import get_settings


PipelineRunStatus = Literal["pending", "running", "completed", "failed"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class PipelineRunStore:
    """Atomic, process-independent pipeline status storage."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or get_settings().RUNS_DIR)

    def create(self, run_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        record = {
            "run_id": run_id,
            "status": "pending",
            "result": None,
            "error": None,
            "input_data": input_data,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        self._write(run_id, record)
        return record

    def get(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else None

    def update(
        self,
        run_id: str,
        status: PipelineRunStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        record = self.get(run_id)
        if record is None:
            raise KeyError(f"Pipeline run not found: {run_id}")
        record.update(
            status=status,
            result=result,
            error=error,
            updated_at=utc_now(),
        )
        if status in {"completed", "failed"}:
            record["completed_at"] = record["updated_at"]
        self._write(run_id, record)
        return record

    def _path(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
            raise ValueError("Invalid pipeline run ID")
        return self.base_dir / f"{run_id}.json"

    def _write(self, run_id: str, payload: dict[str, Any]) -> None:
        path = self._path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".json.{os.getpid()}.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

