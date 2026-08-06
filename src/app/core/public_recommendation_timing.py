from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
import json
import logging
from threading import Lock
from time import perf_counter
from typing import Iterator
from uuid import uuid4

from starlette.datastructures import Headers


logger = logging.getLogger("src.app.performance.public_recommendations")

TIMING_FIELDS = (
    "db_session_ms",
    "db_connection_wait_ms",
    "db_query_ms",
    "db_result_processing_ms",
    "validation_ms",
    "response_model_ms",
    "serialization_ms",
)


class _ProcessRequestState:
    """Identify only the first matching request handled by this process."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._handled_first_request = False

    def claim(self) -> str:
        with self._lock:
            if not self._handled_first_request:
                self._handled_first_request = True
                return "cold"
        return "warm"

    def reset_for_tests(self) -> None:
        with self._lock:
            self._handled_first_request = False


_process_request_state = _ProcessRequestState()


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def _safe_correlation_id(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > 128:
        return None
    if not all(character.isalnum() or character in "-_.:" for character in value):
        return None
    return value


def correlation_id(headers: Headers, state: object) -> str:
    """Reuse common tracing identifiers without trusting arbitrary log text."""
    for attribute in ("trace_id", "request_id"):
        candidate = _safe_correlation_id(getattr(state, attribute, None))
        if candidate:
            return candidate
    for name in ("x-request-id", "x-trace-id"):
        candidate = _safe_correlation_id(headers.get(name))
        if candidate:
            return candidate
    traceparent = headers.get("traceparent", "").split("-")
    if len(traceparent) >= 4:
        candidate = _safe_correlation_id(traceparent[1])
        if candidate:
            return candidate
    return uuid4().hex


@dataclass
class PublicRecommendationTiming:
    trace_id: str
    season: str | None
    gameweek: int | None
    request_state: str
    cache_status: str = "not_configured"
    cache_read_ms: float | None = None
    cache_population_ms: float | None = None
    database_fallback: bool = False
    historical: bool | None = None
    ttl_seconds: int | None = None
    started_at: float = field(default_factory=perf_counter)
    run_id: str | None = None
    failure_stage: str | None = None
    exception_type: str | None = None
    error_category: str | None = None
    active_stage: str = "request_handling"
    timings: dict[str, float] = field(default_factory=dict)

    @contextmanager
    def measure(self, field_name: str, stage: str) -> Iterator[None]:
        if field_name not in TIMING_FIELDS:
            raise ValueError(f"Unsupported performance timing field: {field_name}")
        previous_stage = self.active_stage
        self.active_stage = stage
        started_at = perf_counter()
        try:
            yield
        except Exception as exc:
            self.mark_failure(stage, exc)
            raise
        finally:
            self.timings[field_name] = round(
                self.timings.get(field_name, 0.0) + _elapsed_ms(started_at),
                3,
            )
            self.active_stage = previous_stage

    def mark_failure(
        self,
        stage: str,
        exc: BaseException | None = None,
        *,
        category: str | None = None,
    ) -> None:
        if self.failure_stage is None:
            self.failure_stage = stage
        if exc is not None and self.exception_type is None:
            self.exception_type = type(exc).__name__
        if category is not None and self.error_category is None:
            self.error_category = category

    def summary(self, status_code: int) -> dict[str, object]:
        succeeded = 200 <= status_code < 400
        summary: dict[str, object] = {
            "event": (
                "public_recommendation_lookup_completed"
                if succeeded
                else "public_recommendation_lookup_failed"
            ),
            "trace_id": self.trace_id,
            "season": self.season,
            "gameweek": self.gameweek,
            "request_state": self.request_state,
            "cache_status": self.cache_status,
            "cache_read_ms": self.cache_read_ms,
            "cache_population_ms": self.cache_population_ms,
            "database_fallback": self.database_fallback,
            "historical": self.historical,
            "ttl_seconds": self.ttl_seconds,
            "run_id": self.run_id,
            **{name: self.timings.get(name) for name in TIMING_FIELDS},
            "serialization_status": (
                "measured" if "serialization_ms" in self.timings else "unavailable"
            ),
            "total_ms": _elapsed_ms(self.started_at),
            "status_code": status_code,
            "outcome": "success" if succeeded else "failure",
        }
        if not succeeded:
            summary.update(
                failure_stage=self.failure_stage or self.active_stage,
                exception_type=self.exception_type,
                error_category=self.error_category or _status_category(status_code),
            )
        return summary


def _status_category(status_code: int) -> str:
    if status_code == 404:
        return "report_not_found"
    if status_code == 422:
        return "request_validation_error"
    if status_code >= 500:
        return "server_error"
    return "request_failed"


_current_timing: ContextVar[PublicRecommendationTiming | None] = ContextVar(
    "public_recommendation_timing",
    default=None,
)


def start_timing(
    *, trace_id: str, season: str | None, gameweek: int | None
) -> tuple[PublicRecommendationTiming, Token[PublicRecommendationTiming | None]]:
    timing = PublicRecommendationTiming(
        trace_id=trace_id,
        season=season,
        gameweek=gameweek,
        request_state=_process_request_state.claim(),
    )
    return timing, _current_timing.set(timing)


def finish_timing(token: Token[PublicRecommendationTiming | None]) -> None:
    _current_timing.reset(token)


def current_timing() -> PublicRecommendationTiming | None:
    return _current_timing.get()


@contextmanager
def measure(field_name: str, stage: str) -> Iterator[None]:
    timing = current_timing()
    if timing is None:
        yield
        return
    with timing.measure(field_name, stage):
        yield


def emit_summary(timing: PublicRecommendationTiming, status_code: int) -> None:
    summary = timing.summary(status_code)
    # JSON in the message works with plain formatters; the extra field works with
    # structured logging handlers. Neither includes report or database contents.
    logger.info(
        json.dumps(summary, separators=(",", ":"), sort_keys=True),
        extra={"performance_summary": summary},
    )


def reset_process_request_state_for_tests() -> None:
    _process_request_state.reset_for_tests()
