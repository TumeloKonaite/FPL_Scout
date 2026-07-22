import type { SeasonOption } from "@/src/types/report";

export type ReportSelection = {
  season: string;
  gameweek: number;
};

export function parseReportSelection(params: Pick<URLSearchParams, "get">): ReportSelection | null {
  const season = params.get("season");
  const gameweekValue = params.get("gameweek");
  if (!season && !gameweekValue) return null;
  if (!season || !/^\d{4}-\d{2}$/.test(season) || !gameweekValue) return { season: season ?? "", gameweek: Number.NaN };
  const gameweek = Number(gameweekValue);
  return Number.isInteger(gameweek) && gameweek >= 1 && gameweek <= 38
    ? { season, gameweek }
    : { season, gameweek: Number.NaN };
}

export function selectionExists(seasons: SeasonOption[], selection: ReportSelection): boolean {
  return seasons.some((season) => season.season === selection.season
    && season.gameweeks.some((option) => option.gameweek === selection.gameweek));
}

export function newestSelection(seasons: SeasonOption[]): ReportSelection | null {
  const options = seasons.flatMap((season) => season.gameweeks.map((gameweek) => ({
    season: season.season,
    gameweek: gameweek.gameweek,
    updatedAt: Date.parse(gameweek.last_updated_at) || 0
  })));
  options.sort((a, b) => b.updatedAt - a.updatedAt || b.season.localeCompare(a.season) || b.gameweek - a.gameweek);
  return options[0] ? { season: options[0].season, gameweek: options[0].gameweek } : null;
}

export function seasonLabel(season: string): string {
  return season.replace("-", "/");
}
