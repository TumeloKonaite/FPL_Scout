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


class _RowsResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class _RowsSession:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.statement = None
        self.execute_count = 0

    def __enter__(self) -> _RowsSession:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> _RowsResult:
        self.statement = statement
        self.execute_count += 1
        return _RowsResult(self.rows)


class _RowsSessionFactory:
    def __init__(self, rows: list[object]) -> None:
        self.session = _RowsSession(rows)

    def __call__(self) -> _RowsSession:
        return self.session


def test_public_recommendation_query_is_narrow_and_explicitly_published() -> None:
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
    assert "completed_report_runs.publication_status = 'published'" in sql
    assert "completed_report_runs.final_report IS NOT NULL" in sql
    assert "ORDER BY" not in sql
    assert "LIMIT 1" in sql


def test_public_recommendation_query_returns_none_when_no_row_qualifies() -> None:
    assert (
        ReportRepository(_SessionFactory(None)).latest_public_recommendation(
            "2025-26", 32
        )
        is None
    )


def test_public_gameweek_index_query_is_a_lightweight_published_projection() -> None:
    updated_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    factory = _RowsSessionFactory(
        [
            SimpleNamespace(
                season="2025-26",
                gameweek=32,
                run_id="published-run",
                updated_at=updated_at,
                has_report=True,
                has_suggested_team=True,
                publication_status="published",
            )
        ]
    )

    records = ReportRepository(factory).public_gameweek_index()

    assert len(records) == 1
    assert records[0].run_id == "published-run"
    assert records[0].has_suggested_team is True
    statement = factory.session.statement
    assert statement is not None
    assert list(statement.selected_columns.keys()) == [
        "season",
        "gameweek",
        "run_id",
        "updated_at",
        "has_report",
        "has_suggested_team",
        "publication_status",
    ]
    sql = " ".join(
        str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).split()
    )
    selected_sql = sql.split(" FROM completed_report_runs", maxsplit=1)[0]
    assert "final_report" not in selected_sql
    assert "aggregate_report" not in sql
    assert "expert_outputs" not in sql
    assert "manifest" not in sql
    assert "completed_report_runs.status = 'completed'" in sql
    assert "completed_report_runs.publication_status = 'published'" in sql
    assert "completed_report_runs.has_report IS true" in sql
    assert "final_report" not in sql
    assert (
        "ORDER BY completed_report_runs.season DESC, "
        "completed_report_runs.gameweek DESC, completed_report_runs.run_id DESC"
    ) in sql


def test_public_gameweek_index_uses_one_query_regardless_of_result_count() -> None:
    updated_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(
            season=f"20{index:02d}-{index + 1:02d}",
            gameweek=gameweek,
            run_id=f"run-{index}-{gameweek}",
            updated_at=updated_at,
            has_report=True,
            has_suggested_team=False,
            publication_status="published",
        )
        for index in range(20, 25)
        for gameweek in range(1, 39)
    ]
    factory = _RowsSessionFactory(rows)

    records = ReportRepository(factory).public_gameweek_index()

    assert len(records) == 190
    assert factory.session.execute_count == 1
