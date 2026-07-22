from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest

from src.adapters.fpl import FplApiClient, FplApiError


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _response(events: list[dict]) -> _Response:
    return _Response(json.dumps({"events": events}).encode())


def test_returns_the_official_upcoming_gameweek() -> None:
    events = [
        {"id": 38, "is_current": True, "is_next": False, "deadline_time": "2026-05-24T15:00:00Z"},
        {"id": 1, "is_current": False, "is_next": True, "deadline_time": "2026-08-15T10:00:00Z"},
    ]
    with patch("src.adapters.fpl.urlopen", return_value=_response(events)):
        current = FplApiClient().get_upcoming_gameweek()

    assert current is not None
    assert current.gameweek == 1
    assert current.deadline == "2026-08-15T10:00:00Z"
    assert current.season == "2026-27"


def test_returns_none_when_there_is_no_upcoming_gameweek() -> None:
    with patch("src.adapters.fpl.urlopen", return_value=_response([{"id": 38, "is_current": True, "is_next": False}])):
        assert FplApiClient().get_upcoming_gameweek() is None


def test_caches_the_calendar_result() -> None:
    events = [{"id": 1, "is_next": True, "deadline_time": "2026-08-15T10:00:00Z"}]
    with patch("src.adapters.fpl.urlopen", return_value=_response(events)) as request:
        client = FplApiClient()
        assert client.get_upcoming_gameweek() == client.get_upcoming_gameweek()

    request.assert_called_once()


def test_rejects_an_invalid_calendar_response() -> None:
    with patch("src.adapters.fpl.urlopen", return_value=_Response(b"{}")):
        with pytest.raises(FplApiError):
            FplApiClient().get_upcoming_gameweek()
