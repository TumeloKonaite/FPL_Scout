from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConsensusItem(BaseModel):
    item: str
    mention_count: int = Field(ge=0)
    average_confidence: float = Field(ge=0, le=1)
    supporting_experts: list[str]


class TransferConsensusItem(BaseModel):
    player_name: str
    direction: str
    mention_count: int = Field(ge=0)
    average_confidence: float = Field(ge=0, le=1)
    supporting_experts: list[str]


class FixtureInsightConsensusItem(BaseModel):
    insight: str
    mention_count: int = Field(ge=0)
    supporting_experts: list[str]


class PlayerDisagreementItem(BaseModel):
    player: str
    positive_experts: list[str] = Field(default_factory=list)
    negative_experts: list[str] = Field(default_factory=list)


class CaptaincyDisagreementItem(BaseModel):
    options: list[str] = Field(default_factory=list)
    expert_map: dict[str, list[str]] = Field(default_factory=dict)


class StrategyDisagreementItem(BaseModel):
    side_a: str
    side_a_experts: list[str] = Field(default_factory=list)
    side_b: str
    side_b_experts: list[str] = Field(default_factory=list)


class DisagreementReport(BaseModel):
    players: list[PlayerDisagreementItem] = Field(default_factory=list)
    captaincy: list[CaptaincyDisagreementItem] = Field(default_factory=list)
    strategy: list[StrategyDisagreementItem] = Field(default_factory=list)


class ConditionalAdviceItem(BaseModel):
    expert_name: str
    text: str
    reason: str
    related_entities: list[str] = Field(default_factory=list)


class ExpertTeamRevealItem(BaseModel):
    expert_name: str
    video_title: str
    current_team: list[str] = Field(default_factory=list)
    starting_xi: list[str] = Field(default_factory=list)
    bench: list[str] = Field(default_factory=list)
    player_positions: dict[str, Literal["GK", "DEF", "MID", "FWD"]] = Field(
        default_factory=dict
    )
    captain: str | None = None
    vice_captain: str | None = None
    transfers_in: list[str] = Field(default_factory=list)
    transfers_out: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
