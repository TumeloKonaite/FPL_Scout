from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from src.app.infrastructure.report_repository import ReportRepository


class _Result:
    def __init__(self, row: object | None) -> None:
        self.row = row

    def one_or_none(self) -> object | None:
        return self.row


class _Session:
    def __init__(self, row: object | None) -> None:
        self.row = row
        self.statement = None

    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> _Result:
        self.statement = statement
        return _Result(self.row)


class _SessionFactory:
    def __init__(self, row: object | None) -> None:
        self.session = _Session(row)

    def __call__(self) -> _Session:
        return self.session


def test_public_recommendation_query_is_narrow_filtered_and_deterministic() -> None:
    updated_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    factory = _SessionFactory(
        SimpleNamespace(
            run_id="run-b",
            final_report={"season": "2025-26", "gameweek": 32},
            updated_at=updated_at,
        )
    )

    record = ReportRepository(factory).latest_public_recommendation("2025-26", 32)

    assert record is not None
    assert record.run_id == "run-b"
    statement = factory.session.statement
    assert statement is not None
    assert list(statement.selected_columns.keys()) == [
        "run_id",
        "final_report",
        "updated_at",
    ]
    sql = " ".join(
        str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).split()
    )
    assert "completed_report_runs.aggregate_report" not in sql
    assert "completed_report_runs.expert_outputs" not in sql
    assert "completed_report_runs.manifest" not in sql
    assert "completed_report_runs.season = '2025-26'" in sql
    assert "completed_report_runs.gameweek = 32" in sql
    assert "completed_report_runs.status = 'completed'" in sql
    assert "completed_report_runs.final_report IS NOT NULL" in sql
    assert (
        "ORDER BY completed_report_runs.updated_at DESC, "
        "completed_report_runs.run_id DESC" in sql
    )
    assert "LIMIT 1" in sql


def test_public_recommendation_query_returns_none_when_no_row_qualifies() -> None:
    assert (
        ReportRepository(_SessionFactory(None)).latest_public_recommendation(
            "2025-26", 32
        )
        is None
    )
