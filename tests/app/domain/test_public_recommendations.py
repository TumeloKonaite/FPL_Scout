from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.domain.reports.service import (
    GameweekReportNotFoundError,
    ReportService,
)
from src.app.infrastructure.report_repository import PublicRecommendationRecord


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
