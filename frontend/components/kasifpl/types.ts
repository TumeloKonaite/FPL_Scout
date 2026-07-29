// Public data contracts for the KasiFPL component pack.
// These mirror the FPL_Scout backend Report contract.

export type ConsensusLevel = "strong" | "moderate" | "split";

export type RecommendationSource = {
  name: string;
  title?: string | null;
  url?: string | null;
  publishedAt?: string | null;
  position: "support" | "oppose" | "alternative" | "mention";
};

export type RecommendationConsensus = {
  label: ConsensusLevel;
  supportCount: number;
  relevantExpertCount?: number | null;
  oppositionCount: number;
  mentionCount: number;
  supportRatio?: number | null;
};

export type RecommendationFreshness = {
  generatedAt: string;
  newestSourceAt?: string | null;
  oldestSourceAt?: string | null;
  sourceWindowHours?: number | null;
};

export type RecommendationAlternative = {
  recommendation: string;
  support_count: number;
  sources?: string[];
};

export type FinalRecommendation = {
  title: string;
  rationale: string;
  confidence?: number | null;
  playerName?: string | null;
  club?: string | null;
  opponent?: string | null;
  venue?: "home" | "away" | null;
  consensusCount?: number | null;
  expertCount?: number | null;
  viceCaptain?: string | null;
  playerIn?: string | null;
  playerOut?: string | null;
  position?: string | null;
  price?: number | null;
  consensus?: RecommendationConsensus | null;
  freshness?: RecommendationFreshness | null;
  sources?: RecommendationSource[];
  alternatives?: RecommendationAlternative[];
};

export type PlayerPosition = "GK" | "DEF" | "MID" | "FWD";

export type PlayerSupport = {
  eligibleExpertCount: number;
  starterSupportCount: number;
  starterSupportPercentage: number;
  squadSupportCount: number;
  squadSupportPercentage: number;
  captainSupportCount: number;
  captainSupportPercentage: number;
  viceCaptainSupportCount: number;
  viceCaptainSupportPercentage: number;
  contributingExpertIds: string[];
};

export type SuggestedPlayer = {
  playerId: number;
  officialPlayerId?: number | null;
  name: string;
  canonicalName?: string | null;
  displayName?: string | null;
  number?: number | null;
  shirtNumber?: number | null;
  position: PlayerPosition;
  club?: string | null;
  fixture?: string | null;
  price?: number | null;
  predictedPoints?: number | null;
  ownership?: number | null;
  expectedMinutes?: number | null;
  fixtureDifficulty?: number | null;
  expertSupportCount?: number | null;
  starterSupport?: number;
  benchSupport?: number;
  captainSupport?: number;
  viceCaptainSupport?: number;
  contributingExpertIds?: string[];
  support?: PlayerSupport | null;
  consensus?: string | null;
  captain?: boolean;
  viceCaptain?: boolean;
  isStarter?: boolean;
  benchOrder?: number | null;
};

export type SuggestedTeam = {
  constructionStatus?: "consensus" | "insufficient_evidence";
  failureReason?: string | null;
  constructionMethod?:
    | "vote_based_consensus"
    | "single_reveal"
    | "insufficient_evidence"
    | "legacy_snapshot";
  consensusStrength?: "strong" | "moderate" | "split" | "insufficient";
  provenanceAvailable?: boolean;
  eligibleRevealCount?: number;
  eligibleExpertCount?: number;
  formation?: string | null;
  startingXi?: SuggestedPlayer[];
  starters?: SuggestedPlayer[];
  bench?: SuggestedPlayer[];
  players?: SuggestedPlayer[];
  captainPlayerId?: number | null;
  viceCaptainPlayerId?: number | null;
  warnings?: string[];
};

export type ExpertTeamReveal = {
  expert_name: string;
  summary: string;
  captain?: string | null;
  vice_captain?: string | null;
  transfers_in?: string[];
  transfers_out?: string[];
  confidence?: number | null;
};

export type Disagreement = {
  topic: string;
  summary: string;
  sides?: string[];
};

export type KeyRisk = {
  subject: string;
  riskType?: string | null;
  explanation: string;
  recommendedAction?: string | null;
};

export type Report = {
  gameweek?: number;
  deadline?: string | null;
  lastUpdated?: string | null;
  overview: string;
  transfers?: FinalRecommendation[];
  captaincy?: FinalRecommendation[];
  chip_strategy?: FinalRecommendation[];
  fixture_notes?: string[];
  disagreements?: Disagreement[];
  conditional_advice?: string[];
  wait_for_news?: string[];
  key_risk?: KeyRisk | null;
  expert_team_reveals?: ExpertTeamReveal[];
  suggested_team?: SuggestedTeam | null;
  conclusion: string;
};

export type ReportSelection = {
  season: string;
  gameweek: number;
};

export type NavPage =
  | "briefing"
  | "team"
  | "transfers"
  | "captain"
  | "experts"
  | "archive";

export type NavItem = {
  key: NavPage;
  label: string;
  href: string;
};

export type ArchiveEntry = {
  season: string;
  gameweek: number;
  deadline?: string | null;
  title?: string | null;
  summary?: string | null;
  href: string;
  isCurrent?: boolean;
};
