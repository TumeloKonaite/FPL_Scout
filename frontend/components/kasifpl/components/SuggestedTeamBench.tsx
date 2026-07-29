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
  let outfieldIndex = 0;
  const roleFor = (player: SuggestedPlayer) => {
    if (player.position === "GK") return "Substitute goalkeeper";
    outfieldIndex += 1;
    return `${["First", "Second", "Third"][outfieldIndex - 1] ?? `${outfieldIndex}th`} outfield substitute`;
  };

  return (
    <div>
      <div className="kasifpl-bench">
        <div className="kasifpl-bench__label">Bench</div>
        {ordered.map((p) => (
          <PlayerTile
            key={p.playerId}
            player={p}
            benchRole={roleFor(p)}
            onSelect={interactive ? setSelected : undefined}
          />
        ))}
      </div>
      {interactive ? <PlayerDetailsPopover player={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
