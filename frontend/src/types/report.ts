export type ReportSummary = {
  run_id: string;
  created_at?: string | null;
  title?: string | null;
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
  alternatives?: CompetingRecommendation[];
};

export type ConsensusLevel = "strong" | "moderate" | "split";

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

export type RecommendationSource = {
  name: string;
  title?: string | null;
  url?: string | null;
  publishedAt?: string | null;
  position: "support" | "oppose" | "alternative" | "mention";
};

export type CompetingRecommendation = {
  recommendation: string;
  support_count: number;
  sources?: string[];
};

export type KeyRisk = {
  subject: string;
  riskType?: string | null;
  explanation: string;
  recommendedAction?: string | null;
};

export type FinalDisagreement = {
  topic: string;
  summary: string;
  sides?: string[];
};

export type FinalExpertTeamReveal = {
  expert_name: string;
  summary: string;
  captain?: string | null;
  vice_captain?: string | null;
  transfers_in?: string[];
  transfers_out?: string[];
  confidence?: number | null;
};

export type SuggestedTeam = {
  formation?: string;
  startingXi: import("@/components/suggestedTeam").SuggestedPlayer[];
  starters?: import("@/components/suggestedTeam").SuggestedPlayer[];
  bench?: import("@/components/suggestedTeam").SuggestedPlayer[];
  players?: import("@/components/suggestedTeam").SuggestedPlayer[];
  captainPlayerId?: number | null;
  viceCaptainPlayerId?: number | null;
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
  disagreements?: FinalDisagreement[];
  conditional_advice?: string[];
  wait_for_news?: string[];
  key_risk?: KeyRisk | null;
  expert_team_reveals?: FinalExpertTeamReveal[];
  suggested_team?: SuggestedTeam | null;
  conclusion: string;
  [key: string]: unknown;
};

export type FullReportResponse = {
  season: string;
  gameweek?: number | null;
  last_updated_at?: string | null;
  available: boolean;
  report: Report;
};

export type GameweekOption = {
  gameweek: number;
  last_updated_at: string;
  has_suggested_team: boolean;
};

export type SeasonOption = {
  season: string;
  gameweeks: GameweekOption[];
};

export type AvailableGameweeksResponse = {
  seasons: SeasonOption[];
};

export type CurrentGameweekResponse = {
  gameweek?: number | null;
  deadline?: string | null;
  last_updated_at?: string | null;
  recommendations_available: boolean;
};

export type AdminReportResponse = {
  run_id: string;
  report: Report;
};

export type PipelineRunStatus = "pending" | "queued" | "running" | "completed" | "failed";

export type PipelineRun = {
  run_id: string;
  status: PipelineRunStatus;
  created_at?: string;
  started_at?: string;
  updated_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  current_stage?: string | null;
  error?: string;
  result?: unknown;
};

export type PipelineStatus = {
  status: "idle" | PipelineRunStatus;
  latest_run?: PipelineRun | null;
};
