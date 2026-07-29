import * as React from "react";
import type {
  ConsensusLevel,
  FinalRecommendation,
  PlayerPosition,
  RecommendationConsensus,
  SuggestedPlayer,
  SuggestedTeam,
} from "../types";

/** Format an ISO timestamp for header/deadline display; safe for server. */
export function formatDeadline(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  try {
    return d.toLocaleString(undefined, {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return d.toISOString();
  }
}

export function formatShortDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  try {
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

export function classNames(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function ConsensusChip({ consensus, fallback }: {
  consensus?: RecommendationConsensus | null;
  fallback?: { consensusCount?: number | null; expertCount?: number | null };
}) {
  // Prefer explicit consensus payload.
  if (consensus) {
    const support = consensus.supportCount ?? 0;
    const total = consensus.relevantExpertCount ?? null;
    const label = consensus.label;
    const className =
      label === "strong"
        ? "kasifpl-chip kasifpl-chip--strong"
        : label === "moderate"
          ? "kasifpl-chip kasifpl-chip--moderate"
          : "kasifpl-chip kasifpl-chip--split";
    const text = total != null ? `${support}/${total} experts` : `${support} experts`;
    return (
      <span className={className} title={`${label} consensus`}>
        <span aria-hidden>●</span>
        <span>{text}</span>
      </span>
    );
  }
  // Legacy fallback only.
  const support = fallback?.consensusCount ?? null;
  const total = fallback?.expertCount ?? null;
  if (support == null && total == null) {
    return <span className="kasifpl-chip kasifpl-chip--muted">Consensus unavailable</span>;
  }
  const text = total != null ? `${support ?? 0}/${total} experts` : `${support ?? 0} experts`;
  return (
    <span className="kasifpl-chip kasifpl-chip--moderate">
      <span aria-hidden>●</span>
      <span>{text}</span>
    </span>
  );
}

export function consensusLabel(level?: ConsensusLevel | null): string {
  switch (level) {
    case "strong": return "Strong consensus";
    case "moderate": return "Moderate consensus";
    case "split": return "Split view";
    default: return "Consensus unavailable";
  }
}

/** Supported formation buckets, used by pitch layout. */
export const SUPPORTED_FORMATIONS = [
  "3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-2-3", "5-3-2", "5-4-1",
] as const;

export type FormationTuple = [number, number, number]; // DEF, MID, FWD

export function parseFormation(formation?: string | null): FormationTuple | null {
  if (!formation) return null;
  const cleaned = formation.trim();
  if (!/^\d-\d-\d$/.test(cleaned)) return null;
  const [d, m, f] = cleaned.split("-").map(Number) as [number, number, number];
  if (d + m + f !== 10) return null;
  return [d, m, f];
}

/**
 * Derive the pitch layout from a SuggestedTeam without fabricating players.
 * Returns null when there's not enough evidence to render an XI.
 */
export function buildPitchLayout(team: SuggestedTeam | null | undefined): {
  gk: SuggestedPlayer[];
  def: SuggestedPlayer[];
  mid: SuggestedPlayer[];
  fwd: SuggestedPlayer[];
  formationLabel: string;
} | null {
  if (!team) return null;
  if (team.constructionStatus === "insufficient_evidence") return null;

  const starters =
    (team.startingXi && team.startingXi.length ? team.startingXi : undefined) ??
    (team.starters && team.starters.length ? team.starters : undefined) ??
    (team.players ? team.players.filter((p) => p.isStarter !== false) : undefined);

  if (!starters || starters.length !== 11) return null;
  if (new Set(starters.map((player) => player.playerId)).size !== 11) return null;

  const gk = starters.filter((p) => p.position === "GK");
  const def = starters.filter((p) => p.position === "DEF");
  const mid = starters.filter((p) => p.position === "MID");
  const fwd = starters.filter((p) => p.position === "FWD");
  if (gk.length !== 1) return null;

  const declared = parseFormation(team.formation);
  const derivedFormation = `${def.length}-${mid.length}-${fwd.length}`;
  if (!SUPPORTED_FORMATIONS.includes(derivedFormation as typeof SUPPORTED_FORMATIONS[number])) return null;
  if (team.formation && (!declared || team.formation.trim() !== derivedFormation)) return null;
  return {
    gk,
    def,
    mid,
    fwd,
    formationLabel: derivedFormation,
  };
}

export function positionClass(pos: PlayerPosition): string {
  switch (pos) {
    case "GK": return "kasifpl-player--gk";
    case "DEF": return "kasifpl-player--def";
    case "MID": return "kasifpl-player--mid";
    case "FWD": return "kasifpl-player--fwd";
  }
}

/** Compact one-line label describing a recommendation subject. */
export function recommendationSubject(r: FinalRecommendation): string {
  const parts: string[] = [];
  if (r.playerName) parts.push(r.playerName);
  if (r.club) parts.push(`(${r.club})`);
  return parts.join(" ");
}
