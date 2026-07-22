export const SEASON_FORMAT = /^\d{4}-\d{2}$/;

export type AdminPipelineInput = {
  season: string;
  gameweek: number;
  per_expert_limit: number;
};

export function seasonValidationError(value: string): string | null {
  const season = value.trim();

  if (!season) {
    return "Season is required.";
  }

  if (!SEASON_FORMAT.test(season)) {
    return "Season must use the YYYY-YY format (for example, 2025-26).";
  }

  const startYear = Number(season.slice(0, 4));
  const expectedEndYear = String((startYear + 1) % 100).padStart(2, "0");
  if (season.slice(5) !== expectedEndYear) {
    return "Season must represent consecutive years (for example, 2025-26).";
  }

  return null;
}

export function buildAdminPipelineInput(
  season: string,
  gameweek: string,
  perExpertLimit: string
): AdminPipelineInput {
  return {
    season: season.trim(),
    gameweek: Number(gameweek),
    per_expert_limit: Number(perExpertLimit)
  };
}
