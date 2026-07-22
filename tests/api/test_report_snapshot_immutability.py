from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.core.auth import AdminPrincipal, require_admin
from src.app.core.dependencies import (
    get_current_gameweek_service,
    get_report_service,
)
from src.app.domain.reports.service import ReportService
from src.app.infrastructure.storage.report_store import ReportStore
from src.app.main import create_app


def _final_report(
    *,
    season: str,
    gameweek: int,
    overview: str,
    suggested_team: object = ...,
) -> dict:
    payload = {
        "season": season,
        "gameweek": gameweek,
        "overview": overview,
        "transfers": [
            {
                "title": f"Buy {overview}",
                "rationale": f"Reasoning captured for {overview}",
                "playerName": overview,
                "club": f"{overview} FC",
                "position": "MID",
                "price": 7.5,
            }
        ],
        "captaincy": [],
        "chip_strategy": [],
        "fixture_notes": [],
        "disagreements": [],
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [],
        "conclusion": "Conclusion",
    }
    if suggested_team is not ...:
        payload["suggested_team"] = suggested_team
    return payload


def _aggregate_report(*, season: str, gameweek: int, positions: bool) -> dict:
    names = [f"Player {number}" for number in range(1, 12)]
    position_values = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    return {
        "season": season,
        "gameweek": gameweek,
        "expert_count": 1,
        "player_consensus": [],
        "captaincy_consensus": [],
        "transfer_consensus": [],
        "fixture_insights": [],
        "chip_strategy_consensus": [],
        "disagreements": {"players": [], "captaincy": [], "strategy": []},
        "conditional_advice": [],
        "wait_for_news": [],
        "expert_team_reveals": [
            {
                "expert_name": "Snapshot Expert",
                "video_title": "Complete XI",
                "current_team": names,
                "starting_xi": names,
                "player_positions": (
                    dict(zip(names, position_values, strict=True)) if positions else {}
                ),
                "captain": "Player 9",
            }
        ],
    }


def _write_run(
    root: Path,
    run_id: str,
    *,
    season: str,
    gameweek: int,
    updated_at: str,
    final_report: dict,
    aggregate_report: dict | None = None,
) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    final_path = run_dir / "final_report.json"
    final_path.write_text(json.dumps(final_report), encoding="utf-8")
    if aggregate_report is not None:
        (run_dir / "aggregate_report.json").write_text(
            json.dumps(aggregate_report), encoding="utf-8"
        )
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "season": season,
                "gameweek": gameweek,
                "status": "completed",
                "updated_at": updated_at,
                "report_path": str(final_path),
            }
        ),
        encoding="utf-8",
    )
    return final_path


def _client(reports_dir: Path, current_gameweek: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        ReportStore(reports_dir)
    )
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal()
    if current_gameweek is not None:
        app.dependency_overrides[get_current_gameweek_service] = lambda: current_gameweek
    return TestClient(app)


def test_older_run_response_is_stable_after_conflicting_future_report(tmp_path) -> None:
    season = "2026-27"
    old_final = _final_report(
        season=season,
        gameweek=10,
        overview="Historical Name",
    )
    _write_run(
        tmp_path,
        "old-run",
        season=season,
        gameweek=10,
        updated_at="2026-10-01T12:00:00Z",
        final_report=old_final,
        # The XI deliberately lacks positions. A historical read must not source
        # those positions from any future report.
        aggregate_report=_aggregate_report(season=season, gameweek=10, positions=False),
    )
    client = _client(tmp_path)
    before = client.get("/api/reports/old-run")
    assert before.status_code == 200

    future_final = _final_report(
        season=season,
        gameweek=11,
        overview="Conflicting Future Name",
        suggested_team={
            "formation": "3-4-3",
            "startingXi": [
                {
                    "playerId": number,
                    "name": f"Future Player {number}",
                    "position": position,
                    "club": "Future FC",
                    "price": 12.0,
                    "isStarter": True,
                }
                for number, position in enumerate(
                    ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)],
                    start=1,
                )
            ],
        },
    )
    _write_run(
        tmp_path,
        "future-run",
        season=season,
        gameweek=11,
        updated_at="2026-10-08T12:00:00Z",
        final_report=future_final,
        # These names and positions would previously complete old-run's XI via
        # the global cross-report position catalogue.
        aggregate_report=_aggregate_report(season=season, gameweek=11, positions=True),
    )

    after = client.get("/api/reports/old-run")

    assert after.status_code == 200
    assert after.content == before.content
    assert after.json()["report"]["suggested_team"] is None


def test_legacy_null_and_missing_suggested_teams_are_not_reconstructed(tmp_path) -> None:
    season = "2026-27"
    aggregate = _aggregate_report(season=season, gameweek=9, positions=True)
    _write_run(
        tmp_path,
        "explicit-null",
        season=season,
        gameweek=9,
        updated_at="2026-09-24T12:00:00Z",
        final_report=_final_report(
            season=season,
            gameweek=9,
            overview="Null Snapshot",
            suggested_team=None,
        ),
        aggregate_report=aggregate,
    )
    _write_run(
        tmp_path,
        "missing-field",
        season=season,
        gameweek=8,
        updated_at="2026-09-17T12:00:00Z",
        final_report=_final_report(
            season=season,
            gameweek=8,
            overview="Missing Snapshot",
        ),
        aggregate_report={**aggregate, "gameweek": 8},
    )
    client = _client(tmp_path)

    assert client.get("/api/reports/explicit-null").json()["report"]["suggested_team"] is None
    assert client.get("/api/reports/missing-field").json()["report"]["suggested_team"] is None


def test_new_canonical_run_does_not_modify_older_artifact(tmp_path) -> None:
    season = "2026-27"
    old_path = _write_run(
        tmp_path,
        "canonical-old",
        season=season,
        gameweek=12,
        updated_at="2026-10-29T12:00:00Z",
        final_report=_final_report(
            season=season, gameweek=12, overview="Older Canonical"
        ),
    )
    original_bytes = old_path.read_bytes()
    _write_run(
        tmp_path,
        "canonical-new",
        season=season,
        gameweek=12,
        updated_at="2026-10-30T12:00:00Z",
        final_report=_final_report(
            season=season, gameweek=12, overview="Newer Canonical"
        ),
    )

    response = _client(tmp_path).get(
        "/api/recommendations", params={"season": season, "gameweek": 12}
    )

    assert response.status_code == 200
    assert response.json()["report"]["overview"] == "Newer Canonical"
    assert old_path.read_bytes() == original_bytes


def test_historical_retrieval_does_not_lookup_current_player_data(tmp_path) -> None:
    class FailOnCurrentDataLookup:
        def get_upcoming_gameweek(self):
            raise AssertionError("historical retrieval requested current FPL data")

    season = "2026-27"
    _write_run(
        tmp_path,
        "historical",
        season=season,
        gameweek=7,
        updated_at="2026-09-10T12:00:00Z",
        final_report=_final_report(
            season=season, gameweek=7, overview="Historical Snapshot"
        ),
    )

    response = _client(tmp_path, FailOnCurrentDataLookup()).get(
        "/api/recommendations", params={"season": season, "gameweek": 7}
    )

    assert response.status_code == 200
    assert response.json()["report"]["overview"] == "Historical Snapshot"
