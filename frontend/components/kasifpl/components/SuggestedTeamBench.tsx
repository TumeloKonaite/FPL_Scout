"use client";

import * as React from "react";
import type { SuggestedPlayer, SuggestedTeam } from "../types";
import { PlayerTile, PlayerDetailsPopover } from "./PlayerTile";

export type SuggestedTeamBenchProps = {
  team: SuggestedTeam | null | undefined;
  interactive?: boolean;
};

export function SuggestedTeamBench({ team, interactive = true }: SuggestedTeamBenchProps) {
  const [selected, setSelected] = React.useState<SuggestedPlayer | null>(null);
  if (!team) return null;

  const bench = (team.bench && team.bench.length ? team.bench : undefined)
    ?? (team.players ? team.players.filter((p) => p.isStarter === false) : undefined);

  if (!bench || bench.length === 0) return null;

  const ordered = [...bench].sort((a, b) => (a.benchOrder ?? 0) - (b.benchOrder ?? 0));

  return (
    <div>
      <div className="kasifpl-bench">
        <div className="kasifpl-bench__label">Bench</div>
        {ordered.map((p) => (
          <PlayerTile
            key={p.playerId}
            player={p}
            onSelect={interactive ? setSelected : undefined}
          />
        ))}
      </div>
      {interactive ? <PlayerDetailsPopover player={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
