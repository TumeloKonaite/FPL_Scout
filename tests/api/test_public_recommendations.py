from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.adapters.fpl import CurrentGameweek
from src.app.core.dependencies import (
    get_current_gameweek_service,
    get_report_service,
)
from src.app.domain.reports.service import ReportService
from src.app.infrastructure.storage.report_store import ReportStore
from src.app.main import create_app


class StubCurrentGameweek:
    def get_upcoming_gameweek(self) -> CurrentGameweek:
        return CurrentGameweek(
            gameweek=12,
            deadline="2026-10-30T10:00:00Z",
            season="2026-27",
        )


def _write_report(
    root: Path,
    run_id: str,
    *,
    season: str,
    gameweek: int,
    updated_at: str,
    status: str = "completed",
    suggested_team: bool = False,
) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    payload = {
        "season": season,
        "gameweek": gameweek,
        "overview": f"Overview from {run_id}",
        "transfers": [],
        "captaincy": [],
        "chip_strategy": [],
        "fixture_notes": [],
        "disagreements": [],
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
        "conclusion": "Conclusion",
    }
    if suggested_team:
        payload["suggested_team"] = {"startingXi": []}
    (run_dir / "final_report.json").write_text(json.dumps(payload), encoding="utf-8")
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "season": season,
                "gameweek": gameweek,
                "status": status,
                "updated_at": updated_at,
                "report_path": str(run_dir / "final_report.json"),
            }
        ),
        encoding="utf-8",
    )


def _client(reports_dir: Path) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        ReportStore(reports_dir)
    )
    app.dependency_overrides[get_current_gameweek_service] = StubCurrentGameweek
    return TestClient(app)


def _all_object_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for item in value.values() for key in _all_object_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _all_object_keys(item)}
    return set()


def test_gameweek_index_and_historical_lookup_are_public_and_canonical(
    tmp_path,
) -> None:
    _write_report(
        tmp_path,
        "internal-old",
        season="2026-27",
        gameweek=12,
        updated_at="2026-10-29T15:00:00Z",
    )
    _write_report(
        tmp_path,
        "internal-new",
        season="2026-27",
        gameweek=12,
        updated_at="2026-10-30T15:00:00Z",
        suggested_team=True,
    )
    _write_report(
        tmp_path,
        "prior-season",
        season="2025-26",
        gameweek=38,
        updated_at="2026-05-20T00:00:00Z",
    )
    _write_report(
        tmp_path,
        "failed",
        season="2026-27",
        gameweek=13,
        updated_at="2026-11-01T00:00:00Z",
        status="failed",
    )
    client = _client(tmp_path)

    index = client.get("/api/recommendations/gameweeks")
    historical = client.get(
        "/api/recommendations", params={"season": "2026-27", "gameweek": 12}
    )

    assert index.status_code == 200
    assert index.json() == {
        "seasons": [
            {
                "season": "2026-27",
                "gameweeks": [
                    {
                        "gameweek": 12,
                        "last_updated_at": "2026-10-30T15:00:00Z",
                        "has_suggested_team": True,
                    }
                ],
            },
            {
                "season": "2025-26",
                "gameweeks": [
                    {
                        "gameweek": 38,
                        "last_updated_at": "2026-05-20T00:00:00Z",
                        "has_suggested_team": False,
                    }
                ],
            },
        ]
    }
    assert historical.status_code == 200
    assert historical.json()["season"] == "2026-27"
    assert historical.json()["report"]["overview"] == "Overview from internal-new"
    assert _all_object_keys(historical.json()).isdisjoint(
        {
            "run_id",
            "report_path",
            "manifest_path",
            "run_dir",
            "input_job_path",
            "execution_config",
        }
    )


def test_latest_is_backward_compatible_and_prefers_official_current_report(
    tmp_path,
) -> None:
    _write_report(
        tmp_path,
        "current",
        season="2026-27",
        gameweek=12,
        updated_at="2026-10-30T15:00:00Z",
    )
    _write_report(
        tmp_path,
        "newer-timestamp",
        season="2026-27",
        gameweek=11,
        updated_at="2026-10-31T15:00:00Z",
    )

    response = _client(tmp_path).get("/api/recommendations/latest")

    assert response.status_code == 200
    assert response.json()["season"] == "2026-27"
    assert response.json()["gameweek"] == 12
    assert response.json()["report"]["overview"] == "Overview from current"
    assert "run_id" not in response.json()


def test_missing_historical_report_returns_structured_404(tmp_path) -> None:
    tmp_path.mkdir(exist_ok=True)

    response = _client(tmp_path).get(
        "/api/recommendations", params={"season": "2026-27", "gameweek": 12}
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "REPORT_NOT_FOUND",
            "message": (
                "No completed report is available for season 2026-27, gameweek 12."
            ),
            "details": {"season": "2026-27", "gameweek": 12},
        }
    }


def test_historical_lookup_uses_normal_query_validation(tmp_path) -> None:
    client = _client(tmp_path)

    for params in (
        {"season": "2026-27"},
        {"gameweek": 12},
        {"season": "2026-27", "gameweek": 0},
        {"season": "invalid", "gameweek": 12},
        {"season": "2026-28", "gameweek": 12},
    ):
        response = client.get("/api/recommendations", params=params)
        assert response.status_code == 422
        assert "detail" in response.json()


def test_public_api_does_not_accept_run_id_selection(tmp_path) -> None:
    client = _client(tmp_path)

    query_response = client.get(
        "/api/recommendations", params={"run_id": "internal-run"}
    )
    path_response = client.get("/api/recommendations/internal-run")

    assert query_response.status_code == 422
    assert path_response.status_code == 404
