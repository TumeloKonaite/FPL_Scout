from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.schemas.report_identity import validate_season

from src.schemas.aggregate_report import (
    ConsensusItem,
    ConditionalAdviceItem,
    DisagreementReport,
    ExpertTeamRevealItem,
    FixtureInsightConsensusItem,
    TransferConsensusItem,
    RecommendationSource,
    CompetingRecommendation,
)
from src.services.consensus import ConsensusLevel
from src.schemas.player_resolution import PlayerResolutionEvent


class AggregatedFPLReport(BaseModel):
    season: str
    gameweek: int = Field(ge=1, le=38, strict=True)
    expert_count: int = Field(ge=0)
    player_consensus: list[ConsensusItem]
    captaincy_consensus: list[ConsensusItem]
    transfer_consensus: list[TransferConsensusItem]
    fixture_insights: list[FixtureInsightConsensusItem]
    chip_strategy_consensus: list[ConsensusItem]
    disagreements: DisagreementReport
    conditional_advice: list[ConditionalAdviceItem]
    wait_for_news: list[str]
    expert_team_reveals: list[ExpertTeamRevealItem] = Field(default_factory=list)

    _validate_season = field_validator("season")(validate_season)


class FinalRecommendation(BaseModel):
    title: str
    rationale: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    playerName: str | None = None
    club: str | None = None
    opponent: str | None = None
    venue: Literal["home", "away"] | None = None
    consensusCount: int | None = Field(default=None, ge=0)
    expertCount: int | None = Field(default=None, ge=0)
    viceCaptain: str | None = None
    playerIn: str | None = None
    playerOut: str | None = None
    position: str | None = None
    price: float | None = None
    consensus: "RecommendationConsensus | None" = None
    freshness: "RecommendationFreshness | None" = None
    sources: list[RecommendationSource] = Field(default_factory=list)
    alternatives: list[CompetingRecommendation] = Field(default_factory=list)


class RecommendationConsensus(BaseModel):
    label: ConsensusLevel
    supportCount: int = Field(ge=0)
    relevantExpertCount: int | None = Field(default=None, ge=0)
    oppositionCount: int = Field(default=0, ge=0)
    mentionCount: int = Field(default=0, ge=0)
    supportRatio: float | None = Field(default=None, ge=0, le=1)


class RecommendationFreshness(BaseModel):
    generatedAt: str
    newestSourceAt: str | None = None
    oldestSourceAt: str | None = None
    sourceWindowHours: int | None = Field(default=None, ge=0)


class KeyRisk(BaseModel):
    subject: str
    riskType: str | None = None
    explanation: str
    recommendedAction: str | None = None


class FinalDisagreement(BaseModel):
    topic: str
    summary: str
    sides: list[str] = Field(default_factory=list)


class FinalExpertTeamReveal(BaseModel):
    expert_name: str
    summary: str
    captain: str | None = None
    vice_captain: str | None = None
    transfers_in: list[str] = Field(default_factory=list)
    transfers_out: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SuggestedPlayer(BaseModel):
    playerId: int = Field(gt=0)
    officialPlayerId: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1)
    canonicalName: str | None = None
    displayName: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    number: int | None = Field(default=None, ge=1, le=99)
    shirtNumber: int | None = Field(default=None, ge=1, le=99)
    position: Literal["GK", "DEF", "MID", "FWD"]
    club: str | None = None
    price: float | None = None
    predictedPoints: float | None = None
    ownership: float | None = None
    expectedMinutes: int | None = Field(default=None, ge=0, le=120)
    fixtureDifficulty: int | None = Field(default=None, ge=1, le=5)
    fixture: str | None = None
    expertSupportCount: int | None = Field(default=None, ge=0)
    starterSupport: int = Field(default=0, ge=0)
    benchSupport: int = Field(default=0, ge=0)
    captainSupport: int = Field(default=0, ge=0)
    viceCaptainSupport: int = Field(default=0, ge=0)
    confidenceSum: float = Field(default=0, ge=0)
    contributingExpertIds: list[str] = Field(default_factory=list)
    contributingRevealIds: list[str] = Field(default_factory=list)
    support: "PlayerSupport | None" = None
    consensus: str | None = None
    captain: bool = False
    viceCaptain: bool = False
    isStarter: bool = True
    benchOrder: int | None = Field(default=None, ge=1, le=4)


class SuggestedTeam(BaseModel):
    constructionStatus: Literal["consensus", "insufficient_evidence"] = (
        "insufficient_evidence"
    )
    failureReason: str | None = None
    constructionMethod: "ConstructionMethod" = "insufficient_evidence"
    consensusStrength: "ConsensusStrength" = "insufficient"
    provenanceAvailable: bool = True
    provenance: "SuggestedTeamProvenance | None" = None
    eligibleRevealCount: int = Field(default=0, ge=0)
    eligibleExpertCount: int = Field(default=0, ge=0)
    contributingRevealCount: int = Field(default=0, ge=0)
    contributingExpertCount: int = Field(default=0, ge=0)
    contributingReveals: list["ContributingReveal"] = Field(default_factory=list)
    formation: str | None = None
    startingXi: list[SuggestedPlayer]
    bench: list[SuggestedPlayer] = Field(default_factory=list)
    players: list[SuggestedPlayer] | None = None
    captainPlayerId: int | None = Field(default=None, gt=0)
    viceCaptainPlayerId: int | None = Field(default=None, gt=0)
    catalogueSeason: str | None = None
    catalogueSource: str | None = None
    catalogueFingerprint: str | None = None
    catalogueSnapshotIdentifier: str | None = None
    synthesisDiagnostics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    captaincyValidation: list[str] = Field(default_factory=list)
    resolutionDiagnostics: list[PlayerResolutionEvent] = Field(default_factory=list)


class ContributingReveal(BaseModel):
    expertId: str
    expertName: str
    sourceId: str | None = None
    sourceUrl: str | None = None
    confidence: float = Field(ge=0, le=1)


ConstructionMethod = Literal[
    "vote_based_consensus",
    "single_reveal",
    "insufficient_evidence",
    "legacy_snapshot",
]
ConsensusStrength = Literal["strong", "moderate", "split", "insufficient"]


class PlayerSupport(BaseModel):
    eligibleExpertCount: int = Field(ge=0)
    starterSupportCount: int = Field(ge=0)
    starterSupportPercentage: float = Field(ge=0, le=100)
    squadSupportCount: int = Field(ge=0)
    squadSupportPercentage: float = Field(ge=0, le=100)
    captainSupportCount: int = Field(ge=0)
    captainSupportPercentage: float = Field(ge=0, le=100)
    viceCaptainSupportCount: int = Field(ge=0)
    viceCaptainSupportPercentage: float = Field(ge=0, le=100)
    contributingExpertIds: list[str] = Field(default_factory=list)
    contributingRevealIds: list[str] = Field(default_factory=list)


class ContributingExpert(BaseModel):
    expertId: str
    expertName: str
    revealIds: list[str] = Field(default_factory=list)


class ExcludedReveal(BaseModel):
    revealId: str | None = None
    expertId: str | None = None
    expertName: str | None = None
    sourceId: str | None = None
    sourceTitle: str | None = None
    reasons: list[str] = Field(min_length=1)
    detail: str | None = None


class FormationDerivation(BaseModel):
    method: str
    formation: str | None = None
    positionSource: str
    authoritativeCataloguePositions: bool
    fallbackApplied: str | None = None


class ConsensusStrengthBasis(BaseModel):
    metric: Literal["median_starting_xi_support_percentage"]
    medianSupportPercentage: float | None = Field(default=None, ge=0, le=100)
    minimumExpertRequirement: int = Field(default=2, ge=1)


class SuggestedTeamProvenance(BaseModel):
    constructionMethod: ConstructionMethod
    generatedAt: str
    eligibleRevealCount: int = Field(ge=0)
    eligibleExpertCount: int = Field(ge=0)
    contributingRevealCount: int = Field(ge=0)
    contributingExpertCount: int = Field(default=0, ge=0)
    contributingExperts: list[ContributingExpert] = Field(default_factory=list)
    excludedRevealCount: int = Field(ge=0)
    excludedReveals: list[ExcludedReveal] = Field(default_factory=list)
    formationDerivation: FormationDerivation
    consensusStrength: ConsensusStrength
    consensusStrengthBasis: ConsensusStrengthBasis


class FinalGameweekReport(BaseModel):
    season: str
    gameweek: int = Field(ge=1, le=38, strict=True)
    deadline: str | None = None
    lastUpdated: str | None = None
    overview: str
    transfers: list[FinalRecommendation] = Field(default_factory=list)
    captaincy: list[FinalRecommendation] = Field(default_factory=list)
    chip_strategy: list[FinalRecommendation] = Field(default_factory=list)
    fixture_notes: list[str] = Field(default_factory=list)
    disagreements: list[FinalDisagreement] = Field(default_factory=list)
    conditional_advice: list[str] = Field(default_factory=list)
    wait_for_news: list[str] = Field(default_factory=list)
    key_risk: KeyRisk | None = None
    expert_team_reveals: list[FinalExpertTeamReveal] = Field(default_factory=list)
    suggested_team: SuggestedTeam | None = None
    conclusion: str

    _validate_season = field_validator("season")(validate_season)
