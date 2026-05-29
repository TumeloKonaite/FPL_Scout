export type ReportSummary = {
  run_id: string;
  created_at?: string | null;
  gameweek?: number;
  title?: string | null;
};

export type SuggestedTeam = {
  formation?: string;
  players: unknown[];
};

export type CaptaincyRecommendation = {
  captain: unknown;
  vice_captain?: unknown;
  reasoning?: string;
};

export type TransferRecommendation = {
  player_in?: unknown;
  player_out?: unknown;
  reasoning?: string;
};

export type ExpertConsensus = {
  summary?: string;
  sources?: unknown[];
};

export type FinalRecommendation = {
  title: string;
  rationale: string;
  confidence?: number | null;
};

export type Report = {
  run_id?: string;
  created_at?: string | null;
  gameweek?: number;
  title?: string | null;
  suggested_team?: SuggestedTeam;
  captaincy?: CaptaincyRecommendation | FinalRecommendation[];
  transfers?: TransferRecommendation[] | FinalRecommendation[];
  expert_consensus?: ExpertConsensus;
  [key: string]: unknown;
};

export type FullReportResponse = {
  run_id: string;
  report: Report;
};

export type PipelineRunStatus = "pending" | "running" | "completed" | "failed";

export type PipelineRun = {
  run_id: string;
  status: PipelineRunStatus;
  created_at?: string;
  completed_at?: string;
  error?: string;
  result?: unknown;
};
