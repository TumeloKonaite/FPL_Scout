from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


class FplApiError(RuntimeError):
    """Raised when the official FPL gameweek calendar cannot be read."""


@dataclass(frozen=True, slots=True)
class CurrentGameweek:
    gameweek: int
    deadline: str | None
    season: str | None = None


def _season_from_deadline(deadline: str | None) -> str | None:
    if not deadline:
        return None
    try:
        value = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    except ValueError:
        return None
    start_year = value.year if value.month >= 7 else value.year - 1
    return f"{start_year:04d}-{(start_year + 1) % 100:02d}"


class FplApiClient:
    def __init__(
        self,
        url: str = FPL_BOOTSTRAP_URL,
        timeout_seconds: float = 8.0,
        cache_seconds: float = 300.0,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = cache_seconds
        self._cached_gameweek: CurrentGameweek | None = None
        self._cached_until = 0.0

    def get_upcoming_gameweek(self) -> CurrentGameweek | None:
        if monotonic() < self._cached_until:
            return self._cached_gameweek
        request = Request(
            self.url,
            headers={"Accept": "application/json", "User-Agent": "FPL-Scout/1.0"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed HTTPS service URL
                payload: Any = json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ) as exc:
            raise FplApiError(
                "Could not retrieve the official FPL gameweek calendar"
            ) from exc

        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise FplApiError("The official FPL gameweek calendar response was invalid")

        event = next(
            (
                item
                for item in events
                if isinstance(item, dict) and item.get("is_next") is True
            ),
            None,
        )
        if event is None:
            self._cached_gameweek = None
            self._cached_until = monotonic() + self.cache_seconds
            return None
        gameweek = event.get("id")
        if isinstance(gameweek, bool) or not isinstance(gameweek, int) or gameweek < 1:
            raise FplApiError("The official FPL upcoming gameweek was invalid")
        deadline = event.get("deadline_time")
        self._cached_gameweek = CurrentGameweek(
            gameweek=gameweek,
            deadline=deadline if isinstance(deadline, str) and deadline else None,
            season=_season_from_deadline(
                deadline if isinstance(deadline, str) else None
            ),
        )
        self._cached_until = monotonic() + self.cache_seconds
        return self._cached_gameweek


@lru_cache(maxsize=1)
def get_fpl_api_client() -> FplApiClient:
    return FplApiClient()


__all__ = ["CurrentGameweek", "FplApiClient", "FplApiError", "get_fpl_api_client"]
