from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from fcntl import flock, LOCK_EX, LOCK_UN
from pathlib import Path
from typing import Any, Literal

from src.app.core.config import get_settings


PipelineRunStatus = Literal["queued", "running", "completed", "failed"]


class ActivePipelineRunError(RuntimeError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Pipeline run {run_id} is already active")
        self.run_id = run_id


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
            "status": "queued",
            "result": None,
            "error": None,
            "input_data": input_data,
            "current_stage": "queued",
            "created_at": now,
            "started_at": None,
            "updated_at": now,
            "completed_at": None,
            "duration_seconds": None,
        }
        self._write(run_id, record)
        return record

    def create_if_idle(self, run_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        with self._exclusive_lock():
            active = self.get_active()
            if active is not None:
                raise ActivePipelineRunError(active["run_id"])
            return self.create(run_id, input_data)

    def get(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else None

    def list(self) -> list[dict[str, Any]]:
        if not self.base_dir.exists():
            return []
        records = []
        for path in self.base_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return sorted(records, key=lambda item: str(item.get("created_at") or ""))

    def get_latest(self) -> dict[str, Any] | None:
        records = self.list()
        return records[-1] if records else None

    def get_active(self) -> dict[str, Any] | None:
        return next(
            (record for record in reversed(self.list()) if record.get("status") in {"queued", "running", "pending"}),
            None,
        )

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
        if status == "running":
            record["started_at"] = record.get("started_at") or record["updated_at"]
            record["current_stage"] = "analysis"
        if status in {"completed", "failed"}:
            record["completed_at"] = record["updated_at"]
            record["current_stage"] = None
            started_at = record.get("started_at") or record.get("created_at")
            if started_at:
                started = datetime.fromisoformat(started_at)
                completed = datetime.fromisoformat(record["completed_at"])
                record["duration_seconds"] = max(0.0, (completed - started).total_seconds())
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

    @contextmanager
    def _exclusive_lock(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_dir / ".pipeline.lock"
        with lock_path.open("a+", encoding="utf-8") as handle:
            flock(handle.fileno(), LOCK_EX)
            try:
                yield
            finally:
                flock(handle.fileno(), LOCK_UN)
