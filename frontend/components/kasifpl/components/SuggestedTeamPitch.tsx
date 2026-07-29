"use client";

import * as React from "react";
import type { SuggestedPlayer, SuggestedTeam } from "../types";
import { buildPitchLayout } from "./_shared";
import { PlayerTile, PlayerDetailsPopover } from "./PlayerTile";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type SuggestedTeamPitchProps = {
  team: SuggestedTeam | null | undefined;
  /** Override interactivity — if false, player tiles won't open the popover. */
  interactive?: boolean;
  /** Optional externally-controlled selection for the popover. */
  selectedPlayer?: SuggestedPlayer | null;
  onSelectPlayer?: (player: SuggestedPlayer | null) => void;
};

export function SuggestedTeamPitch({
  team,
  interactive = true,
  selectedPlayer,
  onSelectPlayer,
}: SuggestedTeamPitchProps) {
  const [internalSelected, setInternalSelected] = React.useState<SuggestedPlayer | null>(null);
  const selection = selectedPlayer !== undefined ? selectedPlayer : internalSelected;

  const layout = React.useMemo(() => buildPitchLayout(team), [team]);

  if (!layout) {
    return (
      <SectionUnavailableState
        title="No consensus XI available"
        message={
          team?.failureReason ??
          "There isn't enough expert agreement to construct a suggested starting XI for this gameweek."
        }
      />
    );
  }

  const handleSelect = (p: SuggestedPlayer) => {
    if (!interactive) return;
    if (onSelectPlayer) onSelectPlayer(p);
    else setInternalSelected(p);
  };
  const handleClose = () => {
    if (onSelectPlayer) onSelectPlayer(null);
    else setInternalSelected(null);
  };

  const captainId = team?.captainPlayerId ?? null;
  const viceId = team?.viceCaptainPlayerId ?? null;

  const renderRow = (arr: SuggestedPlayer[], rowClass: string) => (
    <div className={`kasifpl-pitch__row ${rowClass}`}>
      {arr.map((p) => (
        <PlayerTile
          key={p.playerId}
          player={p}
          isCaptain={captainId === p.playerId || p.captain === true}
          isViceCaptain={viceId === p.playerId || p.viceCaptain === true}
          onSelect={handleSelect}
        />
      ))}
    </div>
  );

  return (
    <div>
      <div className="kasifpl-pitch" role="img" aria-label={`Suggested XI, formation ${layout.formationLabel}`}>
        <div className="kasifpl-pitch__stripes" />
        <div className="kasifpl-pitch__lines" />
        {renderRow(layout.gk, "kasifpl-pitch__row--gk")}
        {renderRow(layout.def, "kasifpl-pitch__row--def")}
        {renderRow(layout.mid, "kasifpl-pitch__row--mid")}
        {renderRow(layout.fwd, "kasifpl-pitch__row--fwd")}
      </div>
      {interactive ? <PlayerDetailsPopover player={selection ?? null} onClose={handleClose} /> : null}
    </div>
  );
}
