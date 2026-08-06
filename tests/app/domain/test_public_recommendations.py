from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.domain.reports.service import (
    GameweekReportNotFoundError,
    ReportService,
)
from src.app.infrastructure.report_repository import PublicRecommendationRecord
from src.app.infrastructure.report_repository import PublicGameweekIndexRecord


def _final_report() -> dict:
    return {
        "season": "2025-26",
        "gameweek": 32,
        "overview": "Lightweight report",
        "conclusion": "Conclusion",
    }


class PublicRecommendationRepository:
    def __init__(self, record: PublicRecommendationRecord | None) -> None:
        self.record = record
        self.requested_identity: tuple[str, int] | None = None

    def latest_public_recommendation(
        self, season: str, gameweek: int
    ) -> PublicRecommendationRecord | None:
        self.requested_identity = (season, gameweek)
        return self.record

    def completed_for_gameweek(self, season: str, gameweek: int) -> None:
        raise AssertionError("the full report retrieval path must not be used")


def test_public_recommendation_validates_only_the_final_report() -> None:
    updated_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    repository = PublicRecommendationRepository(
        PublicRecommendationRecord(
            run_id="latest-completed",
            final_report=_final_report(),
            updated_at=updated_at,
        )
    )

    result = ReportService(repository=repository).get_public_recommendation(
        "2025-26", 32
    )

    assert repository.requested_identity == ("2025-26", 32)
    assert result.run_id == "latest-completed"
    assert result.final_report.overview == "Lightweight report"
    assert result.aggregate_report is None
    assert result.updated_at == updated_at.timestamp()


@pytest.mark.parametrize("payload", [None, {"season": "2025-26"}, "malformed"])
def test_public_recommendation_returns_not_found_for_missing_or_invalid_final_report(
    payload: object,
) -> None:
    record = None
    if payload is not None:
        record = PublicRecommendationRecord(
            run_id="invalid",
            final_report=payload,  # type: ignore[arg-type]
            updated_at=datetime.now(timezone.utc),
        )

    with pytest.raises(GameweekReportNotFoundError):
        ReportService(
            repository=PublicRecommendationRepository(record)
        ).get_public_recommendation("2025-26", 32)


class PublicGameweekIndexRepository:
    def __init__(self, rows: list[PublicGameweekIndexRecord]) -> None:
        self.rows = rows

    def public_gameweek_index(self) -> list[PublicGameweekIndexRecord]:
        return self.rows

    def list_published_reports(self) -> None:
        raise AssertionError("the complete report retrieval path must not be used")


def test_gameweek_index_uses_only_projection_metadata_and_sorts_deterministically() -> None:
    updated_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    rows = [
        PublicGameweekIndexRecord(
            season="2024-25",
            gameweek=38,
            run_id="older-season",
            updated_at=updated_at,
            has_report=True,
            has_suggested_team=False,
            publication_status="published",
        ),
        PublicGameweekIndexRecord(
            season="2025-26",
            gameweek=2,
            run_id="newer-season-gw2",
            updated_at=updated_at,
            has_report=True,
            has_suggested_team=True,
            publication_status="published",
        ),
        PublicGameweekIndexRecord(
            season="2025-26",
            gameweek=10,
            run_id="newer-season-gw10",
            updated_at=updated_at,
            has_report=True,
            has_suggested_team=False,
            publication_status="published",
        ),
    ]

    seasons = ReportService(
        repository=PublicGameweekIndexRepository(rows)  # type: ignore[arg-type]
    ).list_available_gameweeks()

    assert [season.season for season in seasons] == ["2025-26", "2024-25"]
    assert [item.gameweek for item in seasons[0].gameweeks] == [10, 2]
    assert [item.has_suggested_team for item in seasons[0].gameweeks] == [False, True]
