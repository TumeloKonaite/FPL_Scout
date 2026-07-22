import type { ReportSelection } from "./reportSelection";

export function isCurrentSelection(
  selection: ReportSelection | null,
  currentGameweek: number | null,
  currentSeason: string | null,
  recommendationsAvailable: boolean
): boolean {
  return Boolean(selection && recommendationsAvailable && currentGameweek === selection.gameweek
    && currentSeason === selection.season);
}

export function deadlineState(deadline: string | null | undefined, historical: boolean, now = Date.now()) {
  if (!deadline) return "missing" as const;
  const timestamp = Date.parse(deadline);
  if (Number.isNaN(timestamp)) return "missing" as const;
  if (historical || timestamp <= now) return "passed" as const;
  return "upcoming" as const;
}
