from __future__ import annotations


PLAYER_IMAGE_URL_TEMPLATE = (
    "https://resources.premierleague.com/premierleague/"
    "photos/players/110x140/p{player_code}.png"
)
TEAM_BADGE_URL_TEMPLATE = (
    "https://resources.premierleague.com/premierleague/"
    "badges/50/t{team_code}.png"
)


def player_image_url(player_code: int | None) -> str | None:
    """Build a progressive-enhancement URL from the PL player code."""
    if not _valid_code(player_code):
        return None
    return PLAYER_IMAGE_URL_TEMPLATE.format(player_code=player_code)


def team_badge_url(team_code: int | None) -> str | None:
    """Build a progressive-enhancement URL from the PL team code."""
    if not _valid_code(team_code):
        return None
    return TEAM_BADGE_URL_TEMPLATE.format(team_code=team_code)


def _valid_code(value: int | None) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


__all__ = [
    "PLAYER_IMAGE_URL_TEMPLATE",
    "TEAM_BADGE_URL_TEMPLATE",
    "player_image_url",
    "team_badge_url",
]
