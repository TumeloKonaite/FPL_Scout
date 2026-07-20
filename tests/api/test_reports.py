from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from src.app.core.dependencies import get_report_service
from src.app.core.dependencies import get_current_gameweek_service
from src.app.core.auth import AdminPrincipal, require_admin
from src.app.domain.reports.service import EmptyReportDirectoryError, ReportNotFoundError
from src.app.main import create_app
from src.schemas.final_report import FinalGameweekReport, SuggestedPlayer, SuggestedTeam
from src.adapters.fpl import CurrentGameweek


@dataclass(frozen=True)
class StubReportSummary:
    run_id: str
    updated_at: float = 1_700_000_000


@dataclass(frozen=True)
class StubReportBundle:
    run_id: str
    final_report: FinalGameweekReport


class StubReportService:
    def __init__(self, reports: dict[str, StubReportBundle] | None = None) -> None:
        self.reports = reports or {}

    def list_reports(self) -> list[StubReportSummary]:
        return [StubReportSummary(run_id) for run_id in self.reports]

    def get_latest_report(self) -> StubReportBundle:
        if not self.reports:
            raise EmptyReportDirectoryError("No reports found")
        return list(self.reports.values())[-1]

    def get_report(self, run_id: str) -> StubReportBundle:
        try:
            return self.reports[run_id]
        except KeyError as exc:
            raise ReportNotFoundError(run_id) from exc


class StubFplApiClient:
    def __init__(self, gameweek: int | None = 32) -> None:
        self.gameweek = gameweek

    def get_upcoming_gameweek(self) -> CurrentGameweek | None:
        if self.gameweek is None:
            return None
        return CurrentGameweek(self.gameweek, "2026-08-15T10:00:00Z")


def _final_report(gameweek: int = 32) -> FinalGameweekReport:
    return FinalGameweekReport(
        gameweek=gameweek,
        overview="Overview",
        transfers=[],
        captaincy=[],
        chip_strategy=[],
        fixture_notes=[],
        disagreements=[],
        conditional_advice=[],
        wait_for_news=[],
        expert_team_reveals=[],
        conclusion="Conclusion",
    )


def _client(service: StubReportService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_report_service] = lambda: service
    app.dependency_overrides[get_current_gameweek_service] = lambda: StubFplApiClient()
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal()
    return TestClient(app)


def test_current_gameweek_does_not_mark_a_stale_report_available() -> None:
    client = _client(StubReportService({"gw38": StubReportBundle("gw38", _final_report(38))}))

    response = client.get("/api/gameweek/current")

    assert response.status_code == 200
    assert response.json()["gameweek"] == 32
    assert response.json()["recommendations_available"] is False


def test_current_gameweek_marks_a_matching_report_available() -> None:
    client = _client(StubReportService({"gw32": StubReportBundle("gw32", _final_report(32))}))

    response = client.get("/api/gameweek/current")

    assert response.status_code == 200
    assert response.json()["deadline"] == "2026-08-15T10:00:00Z"
    assert response.json()["recommendations_available"] is True


def test_list_reports_returns_200_and_a_list() -> None:
    client = _client(
        StubReportService({"gw32": StubReportBundle("gw32", _final_report())})
    )

    response = client.get("/api/reports")

    assert response.status_code == 200
    assert response.json() == [
        {
            "run_id": "gw32",
            "created_at": "2023-11-14T22:13:20+00:00",
            "title": None,
        }
    ]


def test_latest_report_returns_200_when_report_exists() -> None:
    client = _client(
        StubReportService({"gw32": StubReportBundle("gw32", _final_report())})
    )

    response = client.get("/api/reports/latest")

    assert response.status_code == 200
    assert response.json()["run_id"] == "gw32"
    assert response.json()["report"]["gameweek"] == 32


def test_public_latest_recommendations_excludes_internal_run_metadata() -> None:
    client = _client(StubReportService({"internal-run-id": StubReportBundle("internal-run-id", _final_report())}))

    response = client.get("/api/recommendations/latest")

    assert response.status_code == 200
    assert response.json()["gameweek"] == 32
    assert response.json()["available"] is True
    assert "run_id" not in response.json()


def test_latest_report_preserves_structured_suggested_team() -> None:
    positions = ["GK", *(["DEF"] * 3), *(["MID"] * 4), *(["FWD"] * 3)]
    report = _final_report()
    report.suggested_team = SuggestedTeam(
        formation="3-4-3",
        startingXi=[
            SuggestedPlayer(
                playerId=index,
                name=f"Player {index}",
                number=index,
                position=position,
            )
            for index, position in enumerate(positions, start=1)
        ],
    )
    client = _client(StubReportService({"gw32": StubReportBundle("gw32", report)}))

    payload = client.get("/api/reports/latest").json()["report"]["suggested_team"]

    assert payload["formation"] == "3-4-3"
    assert len(payload["startingXi"]) == 11
    assert payload["startingXi"][0] == {
        "playerId": 1,
        "name": "Player 1",
            "number": 1,
            "shirtNumber": None,
        "position": "GK",
        "club": None,
        "price": None,
        "predictedPoints": None,
        "ownership": None,
        "expectedMinutes": None,
            "fixtureDifficulty": None,
            "fixture": None,
            "expertSupportCount": None,
            "consensus": None,
        "captain": False,
        "viceCaptain": False,
            "isStarter": True,
            "benchOrder": None,
    }


def test_latest_report_returns_404_when_no_reports_exist() -> None:
    client = _client(StubReportService())

    response = client.get("/api/reports/latest")

    assert response.status_code == 404
    assert response.json() == {"detail": "No reports found"}


def test_get_report_returns_200_for_existing_report() -> None:
    client = _client(
        StubReportService({"gw32": StubReportBundle("gw32", _final_report())})
    )

    response = client.get("/api/reports/gw32")

    assert response.status_code == 200
    assert response.json()["run_id"] == "gw32"
    assert response.json()["report"]["overview"] == "Overview"


def test_get_report_returns_404_for_missing_report() -> None:
    client = _client(StubReportService())

    response = client.get("/api/reports/gw99")

    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found: gw99"}
