from __future__ import annotations

import re
from dataclasses import dataclass


SEASON_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
MIN_GAMEWEEK = 1
MAX_GAMEWEEK = 38


def parse_season_start_year(season: str) -> int:
    match = SEASON_PATTERN.fullmatch(season)
    if match is None:
        raise ValueError("season must use the YYYY-YY format")
    start_year = int(match.group(1))
    expected_end = (start_year + 1) % 100
    if int(match.group(2)) != expected_end:
        raise ValueError("season end year must be the year after its start year")
    return start_year


def validate_season(season: str) -> str:
    parse_season_start_year(season)
    return season


def validate_gameweek(gameweek: int) -> int:
    if isinstance(gameweek, bool) or not isinstance(gameweek, int):
        raise ValueError("gameweek must be an integer between 1 and 38")
    if not MIN_GAMEWEEK <= gameweek <= MAX_GAMEWEEK:
        raise ValueError("gameweek must be an integer between 1 and 38")
    return gameweek


@dataclass(frozen=True, slots=True)
class ReportIdentity:
    season: str
    gameweek: int

    def __post_init__(self) -> None:
        validate_season(self.season)
        validate_gameweek(self.gameweek)

    @property
    def sort_key(self) -> tuple[int, int]:
        return parse_season_start_year(self.season), self.gameweek
