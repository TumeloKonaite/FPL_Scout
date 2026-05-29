from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex
from typing import Any

from pydantic import BaseModel

from src.app.core.config import get_settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_run_id() -> str:
    return f"{_utc_now().strftime('%Y-%m-%dT%H-%M-%SZ')}_{token_hex(3)}"


def to_serializable(data: Any) -> Any:
    if data is None or isinstance(data, (str, int, float, bool)):
        return data

    if isinstance(data, datetime):
        return _format_timestamp(data)

    if isinstance(data, Path):
        return str(data)

    if is_dataclass(data):
        return to_serializable(asdict(data))

    if isinstance(data, BaseModel):
        return to_serializable(data.model_dump())

    if isinstance(data, Mapping):
        return {str(key): to_serializable(value) for key, value in data.items()}

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        return [to_serializable(item) for item in data]

    if hasattr(data, "dict") and callable(data.dict):
        return to_serializable(data.dict())

    return str(data)


def create_run_folder(base_dir: str | Path | None = None) -> Path:
    base_path = Path(base_dir or get_settings().REPORTS_DIR)
    base_path.mkdir(parents=True, exist_ok=True)

    for _ in range(10):
        run_id = generate_run_id()
        run_path = base_path / run_id
        try:
            run_path.mkdir()
            return run_path
        except FileExistsError:
            continue

    raise RuntimeError("Could not create a unique run folder")


def save_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = to_serializable(data)
    output_path.write_text(
        json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def save_text(path: str | Path, text: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8")


def load_json(path: str | Path) -> dict | list:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_manifest(
    *,
    run_id: str,
    created_at: str,
    artifacts: Mapping[str, str],
    input_jobs: Sequence[Any],
    expert_outputs: Sequence[Any],
    failed_jobs: Sequence[Any] | None = None,
    duplicate_sources: Sequence[Any] | None = None,
    input_mode: str = "youtube_auto",
    configured_experts: int | None = None,
    videos_discovered: int | None = None,
    videos_selected: int | None = None,
    jobs_created: int | None = None,
    transcript_failures: Sequence[Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": created_at,
        "input_mode": input_mode,
        "configured_experts": configured_experts if configured_experts is not None else 0,
        "videos_discovered": videos_discovered if videos_discovered is not None else len(input_jobs),
        "videos_selected": videos_selected if videos_selected is not None else len(input_jobs),
        "jobs_created": jobs_created if jobs_created is not None else len(input_jobs),
        "artifacts": dict(sorted(artifacts.items())),
        "counts": {
            "expert_outputs": len(expert_outputs),
            "failed_jobs": len(failed_jobs or []),
            "input_jobs": len(input_jobs),
            "duplicate_sources": len(duplicate_sources or []),
            "transcript_failures": len(transcript_failures or []),
        },
        "duplicate_sources": to_serializable(duplicate_sources or []),
        "failed_jobs": to_serializable(failed_jobs or []),
        "transcript_failures": to_serializable(transcript_failures or []),
    }


def save_transcript(path: str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = to_serializable(payload)
    output_path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_transcript(path: str) -> dict:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise TypeError("Transcript payload must be a JSON object")
    return payload
