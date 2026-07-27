from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import BaseModel


def to_json_value(data: Any) -> Any:
    if data is None or isinstance(data, (str, int, float, bool)):
        return data
    if isinstance(data, datetime):
        return data.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(data, Path):
        return str(data)
    if is_dataclass(data):
        return to_json_value(asdict(data))
    if isinstance(data, BaseModel):
        return to_json_value(data.model_dump(mode="json"))
    if isinstance(data, Mapping):
        return {str(key): to_json_value(value) for key, value in data.items()}
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        return [to_json_value(item) for item in data]
    return str(data)
