from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.final_report import FinalGameweekReport
from src.schemas.report_identity import ReportIdentity, parse_season_start_year


def _final(**updates):
    payload = {
        "season": "2026-27",
        "gameweek": 1,
        "overview": "Overview",
        "conclusion": "Conclusion",
    }
    payload.update(updates)
    return FinalGameweekReport(**payload)


@pytest.mark.parametrize("season", ["2025-26", "2026-27", "2099-00"])
def test_valid_seasons_are_accepted(season: str) -> None:
    assert _final(season=season).season == season


@pytest.mark.parametrize("season", ["2026", "26-27", "2026/27", "2026-28", "unknown"])
def test_invalid_seasons_are_rejected_for_new_reports(season: str) -> None:
    with pytest.raises(ValidationError):
        _final(season=season)


@pytest.mark.parametrize("gameweek", [0, 39, -1, True])
def test_unsupported_gameweeks_are_rejected(gameweek) -> None:
    with pytest.raises(ValidationError):
        _final(gameweek=gameweek)


def test_missing_identity_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FinalGameweekReport(overview="Overview", conclusion="Conclusion")


def test_identity_parsing_is_centralised() -> None:
    identity = ReportIdentity("2026-27", 12)
    assert identity.sort_key == (2026, 12)
    assert parse_season_start_year(identity.season) == 2026
