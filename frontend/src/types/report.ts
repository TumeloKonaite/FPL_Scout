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
  players?: import("@/components/suggestedTeam").SuggestedPlayer[];
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
  gameweek?: number | null;
  last_updated_at?: string | null;
  available: boolean;
  report: Report;
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
