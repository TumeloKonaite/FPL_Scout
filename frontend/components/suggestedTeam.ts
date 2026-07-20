export const SUPPORTED_FORMATIONS = new Set(["3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-2-3", "5-3-2", "5-4-1"]);

export type PlayerPosition = "GK" | "DEF" | "MID" | "FWD";

export type SuggestedPlayer = {
  playerId: number;
  name: string;
  number?: number | null;
  shirtNumber?: number | null;
  position: PlayerPosition;
  club?: string | null;
  team?: string | null;
  fixture?: string | null;
  price?: number | null;
  predictedPoints?: number | null;
  ownership?: number | null;
  expectedMinutes?: number | null;
  fixtureDifficulty?: number | null;
  expertSupportCount?: number | null;
  consensus?: string | null;
  captain?: boolean;
  viceCaptain?: boolean;
  isStarter?: boolean;
  benchOrder?: number | null;
};

export type SuggestedTeamInput = {
  formation?: string | null;
  startingXi?: SuggestedPlayer[];
  starters?: SuggestedPlayer[];
  bench?: SuggestedPlayer[];
  players?: SuggestedPlayer[];
  captainPlayerId?: number | null;
  viceCaptainPlayerId?: number | null;
};

export type GroupedPlayers = {
  goalkeeper: SuggestedPlayer[];
  defenders: SuggestedPlayer[];
  midfielders: SuggestedPlayer[];
  forwards: SuggestedPlayer[];
};

export type NormalizedSuggestedTeam = {
  starters: SuggestedPlayer[];
  bench: SuggestedPlayer[];
  allPlayers: SuggestedPlayer[];
  groupedPlayers: GroupedPlayers;
  formation: string | null;
  captain: SuggestedPlayer | null;
  viceCaptain: SuggestedPlayer | null;
  warnings: string[];
  completeStartingXi: boolean;
};

const POSITIONS = new Set<PlayerPosition>(["GK", "DEF", "MID", "FWD"]);

export function groupPlayersByPosition(players: SuggestedPlayer[]): GroupedPlayers {
  return {
    goalkeeper: players.filter((player) => player.position === "GK"),
    defenders: players.filter((player) => player.position === "DEF"),
    midfielders: players.filter((player) => player.position === "MID"),
    forwards: players.filter((player) => player.position === "FWD")
  };
}

export function deriveFormation(players: SuggestedPlayer[]): string | null {
  const grouped = groupPlayersByPosition(players);
  if (grouped.goalkeeper.length !== 1 || players.length !== 11) return null;
  const formation = `${grouped.defenders.length}-${grouped.midfielders.length}-${grouped.forwards.length}`;
  return SUPPORTED_FORMATIONS.has(formation) ? formation : null;
}

function usablePlayer(player: SuggestedPlayer): boolean {
  return Number.isInteger(player.playerId) && player.playerId > 0 && typeof player.name === "string" && Boolean(player.name.trim()) && POSITIONS.has(player.position);
}

function uniquePlayers(players: SuggestedPlayer[], warnings: string[]): SuggestedPlayer[] {
  const ids = new Set<number>();
  return players.filter((player) => {
    if (!usablePlayer(player)) {
      warnings.push("Some players with missing required details could not be displayed.");
      return false;
    }
    if (ids.has(player.playerId)) {
      warnings.push("Duplicate players were removed from the suggested team.");
      return false;
    }
    ids.add(player.playerId);
    return true;
  });
}

export function normalizeSuggestedTeam(team?: SuggestedTeamInput | null): NormalizedSuggestedTeam | null {
  if (!team) return null;
  const warnings: string[] = [];
  const explicitStarters = team.startingXi ?? team.starters;
  const sourcePlayers = team.players ?? [];
  const rawStarters = explicitStarters ?? sourcePlayers.filter((player) => player.isStarter !== false && player.benchOrder == null);
  const starterIds = new Set(rawStarters.map((player) => player.playerId));
  const rawBench = team.bench ?? sourcePlayers.filter((player) => player.isStarter === false || player.benchOrder != null).filter((player) => !starterIds.has(player.playerId));
  const starters = uniquePlayers(rawStarters, warnings).map((player) => ({ ...player, isStarter: true }));
  const starterIdSet = new Set(starters.map((player) => player.playerId));
  const bench = uniquePlayers(rawBench.filter((player) => !starterIdSet.has(player.playerId)), warnings)
    .map((player, index) => ({ ...player, isStarter: false, benchOrder: player.benchOrder ?? index + 1 }))
    .sort((a, b) => (a.benchOrder ?? 99) - (b.benchOrder ?? 99));
  const groupedPlayers = groupPlayersByPosition(starters);
  const derivedFormation = deriveFormation(starters);
  const suppliedFormation = team.formation && SUPPORTED_FORMATIONS.has(team.formation) ? team.formation : null;
  const formation = derivedFormation ?? suppliedFormation;

  if (starters.length !== 11) warnings.push(`Expected 11 starters but received ${starters.length}.`);
  if (!derivedFormation) warnings.push("A standard formation could not be derived; players are shown by position.");
  else if (suppliedFormation && suppliedFormation !== derivedFormation) warnings.push(`The supplied formation did not match the players; ${derivedFormation} is shown instead.`);
  if (bench.length !== 4) warnings.push(`Expected 4 substitutes but received ${bench.length}.`);

  const allPlayers = [...starters, ...bench];
  const captain = allPlayers.find((player) => player.playerId === team.captainPlayerId) ?? allPlayers.find((player) => player.captain) ?? null;
  const viceCaptain = allPlayers.find((player) => player.playerId === team.viceCaptainPlayerId) ?? allPlayers.find((player) => player.viceCaptain) ?? null;
  if (!captain) warnings.push("Captain information is not available.");
  if (!viceCaptain) warnings.push("Vice-captain information is not available.");

  return {
    starters,
    bench,
    allPlayers,
    groupedPlayers,
    formation,
    captain,
    viceCaptain,
    warnings: [...new Set(warnings)],
    completeStartingXi: starters.length === 11 && derivedFormation !== null
  };
}

export function validateStartingXi(players: SuggestedPlayer[], suppliedFormation?: string) {
  if (players.some((player) => player.number !== undefined && player.number !== null && (!Number.isInteger(player.number) || player.number < 1 || player.number > 99))) {
    return { valid: false as const, reason: "invalid-player-number" };
  }
  const normalized = normalizeSuggestedTeam({ startingXi: players, formation: suppliedFormation });
  if (!normalized?.completeStartingXi) return { valid: false as const, reason: "incomplete-or-invalid" };
  if (suppliedFormation !== undefined && normalized.formation !== suppliedFormation) return { valid: false as const, reason: "formation-mismatch" };
  return { valid: true as const, formation: normalized.formation!, groupedPlayers: normalized.groupedPlayers };
}

export function playerLabel(player: SuggestedPlayer, captainId?: number, viceCaptainId?: number): string {
  if (player.playerId === captainId || player.captain) return `${player.name} (C)`;
  if (player.playerId === viceCaptainId || player.viceCaptain) return `${player.name} (VC)`;
  return player.name;
}

export function describeLineup(formation: string | null, grouped: GroupedPlayers): string {
  const names = (players: SuggestedPlayer[]) => players.map((player) => playerLabel(player)).join(", ") || "Not available";
  return `Suggested formation ${formation ?? "not available"}. Goalkeeper: ${names(grouped.goalkeeper)}. Defenders: ${names(grouped.defenders)}. Midfielders: ${names(grouped.midfielders)}. Forwards: ${names(grouped.forwards)}.`;
}
