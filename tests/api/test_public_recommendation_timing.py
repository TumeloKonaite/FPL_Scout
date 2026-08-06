from __future__ import annotations

from datetime import datetime, timezone
import logging
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.app.core.dependencies import get_report_service
from src.app.core.public_recommendation_timing import (
    reset_process_request_state_for_tests,
)
from src.app.domain.reports.service import ReportService
from src.app.infrastructure.report_repository import ReportRepository
from src.app.main import create_app


LOGGER_NAME = "src.app.performance.public_recommendations"


class _Result:
    def __init__(self, row: object | None) -> None:
        self.row = row

    def one_or_none(self) -> object | None:
        return self.row


class _Session:
    def __init__(self, row: object | None, error: Exception | None = None) -> None:
        self.row = row
        self.error = error

    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def connection(self) -> object:
        return object()

    def execute(self, statement: object) -> _Result:
        del statement
        if self.error is not None:
            raise self.error
        return _Result(self.row)


class _SessionFactory:
    def __init__(self, row: object | None, error: Exception | None = None) -> None:
        self.row = row
        self.error = error

    def __call__(self) -> _Session:
        return _Session(self.row, self.error)


def _stored_report(marker: str = "public overview") -> dict[str, Any]:
    return {
        "season": "2025-26",
        "gameweek": 32,
        "overview": marker,
        "conclusion": "Conclusion",
    }


def _row(payload: object, run_id: str = "selected-run") -> object:
    return SimpleNamespace(
        run_id=run_id,
        final_report=payload,
        updated_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
    )


def _client(
    row: object | None,
    *,
    error: Exception | None = None,
    raise_server_exceptions: bool = True,
) -> TestClient:
    repository = ReportRepository(_SessionFactory(row, error))
    app = create_app()
    app.dependency_overrides[get_report_service] = lambda: ReportService(repository)
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _summaries(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        record.performance_summary
        for record in caplog.records
        if record.name == LOGGER_NAME and hasattr(record, "performance_summary")
    ]


def _single_summary(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    summaries = _summaries(caplog)
    assert len(summaries) == 1
    return summaries[0]


@pytest.fixture(autouse=True)
def _reset_cold_start_marker() -> None:
    reset_process_request_state_for_tests()


def test_success_emits_one_complete_stage_summary_and_trace_header(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "payload-must-not-appear-in-performance-log"
    client = _client(_row(_stored_report(marker)))

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 32},
            headers={"X-Request-ID": "upstream-request-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "upstream-request-123"
    summary = _single_summary(caplog)
    assert summary["event"] == "public_recommendation_lookup_completed"
    assert summary["trace_id"] == "upstream-request-123"
    assert summary["season"] == "2025-26"
    assert summary["gameweek"] == 32
    assert summary["run_id"] == "selected-run"
    assert summary["request_state"] == "cold"
    assert summary["cache_status"] == "not_configured"
    assert summary["serialization_status"] == "measured"
    assert summary["status_code"] == 200
    for field in (
        "db_session_ms",
        "db_connection_wait_ms",
        "db_query_ms",
        "db_result_processing_ms",
        "validation_ms",
        "response_model_ms",
        "serialization_ms",
        "total_ms",
    ):
        assert isinstance(summary[field], float)
        assert summary[field] >= 0
    assert marker not in caplog.text


def test_not_found_emits_failure_summary_with_generated_trace_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = _client(None).get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 32},
        )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"]
    summary = _single_summary(caplog)
    assert summary["event"] == "public_recommendation_lookup_failed"
    assert summary["trace_id"] == response.headers["X-Request-ID"]
    assert summary["error_category"] == "report_not_found"
    assert summary["status_code"] == 404
    assert summary["season"] == "2025-26"
    assert summary["gameweek"] == 32


def test_invalid_stored_report_identifies_validation_without_logging_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    invalid_payload = {"overview": "private-invalid-report-marker"}

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = _client(_row(invalid_payload, "invalid-run")).get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 32},
        )

    assert response.status_code == 404
    summary = _single_summary(caplog)
    assert summary["run_id"] == "invalid-run"
    assert summary["failure_stage"] == "final_report_validation"
    assert summary["error_category"] == "invalid_stored_report"
    assert isinstance(summary["validation_ms"], float)
    assert summary["validation_ms"] >= 0
    assert "private-invalid-report-marker" not in caplog.text


def test_database_failure_emits_query_timing_and_safe_error_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _client(
        None,
        error=RuntimeError("secret-database-value"),
        raise_server_exceptions=False,
    )

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 32},
        )

    assert response.status_code == 500
    summary = _single_summary(caplog)
    assert summary["failure_stage"] == "db_query"
    assert summary["exception_type"] == "RuntimeError"
    assert summary["error_category"] == "server_error"
    assert isinstance(summary["db_query_ms"], float)
    assert summary["db_query_ms"] >= 0
    assert summary["serialization_ms"] is None
    assert summary["serialization_status"] == "unavailable"
    assert "secret-database-value" not in caplog.text


def test_first_request_is_cold_and_following_request_is_warm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _client(_row(_stored_report()))

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        for _ in range(2):
            assert (
                client.get(
                    "/api/recommendations",
                    params={"season": "2025-26", "gameweek": 32},
                ).status_code
                == 200
            )

    assert [item["request_state"] for item in _summaries(caplog)] == ["cold", "warm"]


def test_request_validation_failure_still_emits_exactly_one_summary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = _client(_row(_stored_report())).get(
            "/api/recommendations",
            params={"season": "2025-26"},
        )

    assert response.status_code == 422
    summary = _single_summary(caplog)
    assert summary["season"] == "2025-26"
    assert summary["gameweek"] is None
    assert summary["error_category"] == "request_validation_error"
    assert summary["serialization_status"] == "unavailable"
