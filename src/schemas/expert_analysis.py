from typing import Literal

from pydantic import BaseModel, Field


class ExpertVideoAnalysis(BaseModel):
    expert_name: str
    video_title: str
    gameweek: int
    summary: str
    key_takeaways: list[str]
    recommended_players: list[str]
    avoid_players: list[str]
    captaincy_picks: list[str]
    chip_strategy: str | None = None
    reasoning: list[str]
    confidence: Literal["low", "medium", "high"]
    current_team: list[str] = Field(default_factory=list)
    starting_xi: list[str] = Field(default_factory=list)
    bench: list[str] = Field(default_factory=list)
    player_positions: dict[str, Literal["GK", "DEF", "MID", "FWD"]] = Field(
        default_factory=dict,
        description=(
            "FPL positions for players named in the team-reveal fields, keyed by "
            "the same clean player names used in those fields"
        ),
    )
    captain: str | None = None
    vice_captain: str | None = None
    transfers_in: list[str] = Field(default_factory=list)
    transfers_out: list[str] = Field(default_factory=list)
    team_reveal_confidence: Literal["low", "medium", "high"] | None = None
    published_at: str | None = None
    source_url: str | None = None
