export type ReportSummary = {
  run_id: string;
  created_at?: string | null;
  title?: string | null;
};

export type FinalRecommendation = {
  title: string;
  rationale: string;
  confidence?: number | null;
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
  overview: string;
  transfers?: FinalRecommendation[];
  captaincy?: FinalRecommendation[];
  chip_strategy?: FinalRecommendation[];
  fixture_notes?: string[];
  disagreements?: FinalDisagreement[];
  conditional_advice?: string[];
  wait_for_news?: string[];
  expert_team_reveals?: FinalExpertTeamReveal[];
  suggested_team?: SuggestedTeam | null;
  conclusion: string;
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
