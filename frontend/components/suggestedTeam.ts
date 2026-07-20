import type { Team } from "react-soccer-lineup";

export const SUPPORTED_FORMATIONS = new Set(["3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-2-3", "5-3-2", "5-4-1"]);

export type PlayerPosition = "GK" | "DEF" | "MID" | "FWD";

export type SuggestedPlayer = {
  playerId: number;
  name: string;
  number: number;
  position: PlayerPosition;
  club?: string | null;
  price?: number | null;
  predictedPoints?: number | null;
  ownership?: number | null;
  expectedMinutes?: number | null;
  fixtureDifficulty?: number | null;
  captain?: boolean;
  viceCaptain?: boolean;
  isStarter?: boolean;
};

export type GroupedPlayers = {
  goalkeeper: SuggestedPlayer[];
  defenders: SuggestedPlayer[];
  midfielders: SuggestedPlayer[];
  forwards: SuggestedPlayer[];
};

export type LineupValidationResult =
  | { valid: true; formation: string; groupedPlayers: GroupedPlayers }
  | { valid: false; reason: string };

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
  if (grouped.goalkeeper.length !== 1) return null;
  return `${grouped.defenders.length}-${grouped.midfielders.length}-${grouped.forwards.length}`;
}

export function validateStartingXi(players: SuggestedPlayer[], suppliedFormation?: string): LineupValidationResult {
  if (!Array.isArray(players)) return { valid: false, reason: "missing-lineup" };
  if (players.length !== 11) return { valid: false, reason: "player-count" };

  const ids = new Set<number>();
  for (const player of players) {
    if (!POSITIONS.has(player.position)) return { valid: false, reason: "unsupported-position" };
    if (!Number.isInteger(player.playerId) || player.playerId <= 0) return { valid: false, reason: "invalid-player-id" };
    if (ids.has(player.playerId)) return { valid: false, reason: "duplicate-player-id" };
    ids.add(player.playerId);
    if (typeof player.name !== "string" || !player.name.trim()) return { valid: false, reason: "missing-player-name" };
    if (!Number.isInteger(player.number) || player.number < 1 || player.number > 99) return { valid: false, reason: "invalid-player-number" };
  }

  const groupedPlayers = groupPlayersByPosition(players);
  const formation = deriveFormation(players);
  if (
    groupedPlayers.goalkeeper.length !== 1 ||
    groupedPlayers.defenders.length < 3 || groupedPlayers.defenders.length > 5 ||
    groupedPlayers.midfielders.length < 2 || groupedPlayers.midfielders.length > 5 ||
    groupedPlayers.forwards.length < 1 || groupedPlayers.forwards.length > 3 ||
    formation === null || !SUPPORTED_FORMATIONS.has(formation)
  ) return { valid: false, reason: "unsupported-formation" };
  if (suppliedFormation !== undefined && suppliedFormation !== formation) return { valid: false, reason: "formation-mismatch" };
  return { valid: true, formation, groupedPlayers };
}

const toPitchPlayer = (player: SuggestedPlayer) => ({ name: player.name, number: player.number });

export function mapPlayersToLineup(grouped: GroupedPlayers): Team {
  return {
    squad: {
      gk: toPitchPlayer(grouped.goalkeeper[0]),
      df: grouped.defenders.map(toPitchPlayer),
      cm: grouped.midfielders.map(toPitchPlayer),
      fw: grouped.forwards.map(toPitchPlayer)
    },
    style: {
      color: "#f7f9f8",
      borderColor: "#17241f",
      numberColor: "#17241f",
      nameColor: "#ffffff",
      nameBackgroundColor: "rgba(12, 36, 27, .88)",
      nameOverflow: "ellipsis",
      pattern: "none"
    }
  };
}

export function describeLineup(formation: string, grouped: GroupedPlayers): string {
  const names = (players: SuggestedPlayer[]) => players.map((player) => player.name).join(", ");
  return `Suggested formation ${formation}. Goalkeeper: ${names(grouped.goalkeeper)}. Defenders: ${names(grouped.defenders)}. Midfielders: ${names(grouped.midfielders)}. Forwards: ${names(grouped.forwards)}.`;
}
