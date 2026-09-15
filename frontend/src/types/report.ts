import type { Report } from "@/components/kasifpl";

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

export type PipelineRunStatus = "pending" | "queued" | "running" | "completed" | "failed";

export type PipelineRun = {
  run_id: string;
  status: PipelineRunStatus;
  created_at?: string;
  started_at?: string;
  updated_at?: string;
  heartbeat_at?: string;
  lease_expires_at?: string;
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
