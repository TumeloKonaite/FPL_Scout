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

const FRIENDLY_FAILURES: Record<string, string> = {
  authoritative_player_catalogue_unavailable: "Player data is temporarily unavailable, so a verified XI cannot be built.",
  player_catalogue_season_mismatch: "Player data for this season is not available yet.",
  no_eligible_reveals: "No usable expert team information was found for this gameweek.",
  insufficient_contributing_experts: "Not enough verified expert team information was found to build an XI.",
  insufficient_resolved_players: "There are not enough verified players in the required positions to build a legal XI.",
  no_valid_starting_formation: "The verified players do not fit a legal starting formation.",
  no_valid_full_squad: "A complete verified squad could not be built.",
  insufficient_captaincy_evidence: "There is not enough verified captaincy information to publish this XI.",
};

function unavailableMessage(team: SuggestedTeam | null | undefined): string {
  const diagnostic = team?.synthesisDiagnostics?.failureMessage;
  if (typeof diagnostic === "string" && diagnostic.trim()) return diagnostic;
  if (team?.failureReason && FRIENDLY_FAILURES[team.failureReason]) {
    return FRIENDLY_FAILURES[team.failureReason];
  }
  return "There isn't enough expert information to construct a suggested starting XI for this gameweek.";
}

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
        title="Suggested XI unavailable"
        message={unavailableMessage(team)}
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
