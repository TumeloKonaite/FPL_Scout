from __future__ import annotations

from types import SimpleNamespace

from src.services.historical_regeneration_service import (
    HistoricalRegenerationService,
    build_contamination_inventory,
)


class InventoryRepository:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def reports_for_range(self, *args, **kwargs):
        return self.rows


def test_dry_run_inventory_does_not_execute_pipeline() -> None:
    calls = []
    service = HistoricalRegenerationService(
        InventoryRepository(),
        pipeline_runner=lambda **kwargs: calls.append(kwargs),
    )

    summary = service.regenerate(
        season="2025-26",
        from_gameweek=30,
        to_gameweek=37,
        deadlines={gameweek: "2026-03-14T13:30:00Z" for gameweek in range(30, 38)},
        command="regenerate --dry-run",
        dry_run=True,
    )

    assert calls == []
    assert summary["missing_gameweeks"] == list(range(30, 38))
    assert summary["report_count"] == 0


def test_inventory_classifies_legacy_missing_evidence_as_unverifiable() -> None:
    row = SimpleNamespace(
        season="2025-26",
        gameweek=30,
        run_id="legacy",
        status="completed",
        discovered_videos=[
            {
                "selected": True,
                "video_id": "abcdefghijk",
                "title": "FPL GW38 experts team",
                "video_url": "https://www.youtube.com/watch?v=abcdefghijk",
                "published_at": "2026-05-20T10:00:00Z",
            }
        ],
        input_jobs=[],
    )

    inventory = build_contamination_inventory(
        repository=InventoryRepository([row]),
        season="2025-26",
        from_gameweek=30,
        to_gameweek=30,
        deadlines={30: "2026-03-14T13:30:00Z"},
    )

    report = inventory["reports"][0]
    assert report["validation_passed"] is False
    assert report["provenance_classification"] == (
        "contaminated_or_unverifiable"
    )
    assert report["source_validations"][0]["rejection_reason"] == (
        "title_mentions_different_gameweek"
    )


def test_identical_fingerprint_detection_reports_other_gameweek() -> None:
    collisions, overlaps = HistoricalRegenerationService._reuse_evidence(
        gameweek=31,
        fingerprint="same",
        video_ids=["a", "b"],
        seen={30: ("same", ["a", "b"])},
        threshold=0.75,
    )

    assert collisions == [30]
    assert overlaps == [{"gameweek": 30, "overlap": 1.0, "adjacent": True}]
