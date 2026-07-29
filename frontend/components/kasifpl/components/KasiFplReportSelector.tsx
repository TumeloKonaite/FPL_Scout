"use client";

import * as React from "react";
import type { ReportSelection } from "../types";
import { formatDeadline } from "./_shared";

export type KasiFplReportSelectorProps = {
  selection: ReportSelection;
  availableSeasons: string[];
  availableGameweeks: number[];
  onSeasonChange?: (season: string) => void;
  onGameweekChange?: (gameweek: number) => void;
  deadline?: string | null;
  isCurrentReport?: boolean;
  disabled?: boolean;
};

export function KasiFplReportSelector({
  selection,
  availableSeasons,
  availableGameweeks,
  onSeasonChange,
  onGameweekChange,
  deadline,
  isCurrentReport,
  disabled,
}: KasiFplReportSelectorProps) {
  const seasonId = React.useId();
  const gwId = React.useId();

  return (
    <div className="kasifpl-selector" role="group" aria-label="Report selection">
      <div className="kasifpl-selector__group">
        <label htmlFor={seasonId} className="kasifpl-selector__label">Season</label>
        <select
          id={seasonId}
          className="kasifpl-selector__select"
          value={selection.season}
          disabled={disabled || !onSeasonChange}
          onChange={(e) => onSeasonChange?.(e.target.value)}
        >
          {availableSeasons.length === 0 ? (
            <option value={selection.season}>{selection.season}</option>
          ) : (
            availableSeasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))
          )}
        </select>
      </div>
      <div className="kasifpl-selector__group">
        <label htmlFor={gwId} className="kasifpl-selector__label">Gameweek</label>
        <select
          id={gwId}
          className="kasifpl-selector__select"
          value={selection.gameweek}
          disabled={disabled || !onGameweekChange}
          onChange={(e) => onGameweekChange?.(Number(e.target.value))}
        >
          {availableGameweeks.length === 0 ? (
            <option value={selection.gameweek}>GW {selection.gameweek}</option>
          ) : (
            availableGameweeks.map((gw) => (
              <option key={gw} value={gw}>GW {gw}</option>
            ))
          )}
        </select>
      </div>
      {isCurrentReport ? (
        <span className="kasifpl-chip kasifpl-chip--strong" aria-label="Current gameweek">Current</span>
      ) : null}
      {deadline ? (
        <div className="kasifpl-selector__deadline">
          <span>Deadline</span>
          <strong>{formatDeadline(deadline)}</strong>
        </div>
      ) : null}
    </div>
  );
}
