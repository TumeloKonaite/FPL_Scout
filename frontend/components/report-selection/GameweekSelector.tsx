"use client";

import { useSelectedReport } from "@/components/useSelectedReport";

export function GameweekSelector() {
  const { selection, availableSeasons, availableGameweeks, isLoadingIndex, setSeason, setGameweek } = useSelectedReport();
  const disabled = isLoadingIndex || !availableSeasons.length;
  return (
    <div className="report-selector" aria-label="Select report">
      <label>Season
        <select aria-label="Season" disabled={disabled} value={selection?.season ?? ""} onChange={(event) => setSeason(event.target.value)}>
          {!selection ? <option value="">{isLoadingIndex ? "Loading…" : "Unavailable"}</option> : null}
          {availableSeasons.map((option) => <option value={option.season} key={option.season}>{option.season.replace("-", "/")}</option>)}
        </select>
      </label>
      <label>Gameweek
        <select aria-label="Gameweek" disabled={disabled || !selection} value={Number.isInteger(selection?.gameweek) ? selection?.gameweek : ""} onChange={(event) => setGameweek(Number(event.target.value))}>
          {!selection || !Number.isInteger(selection.gameweek) ? <option value="">{isLoadingIndex ? "Loading…" : "Unavailable"}</option> : null}
          {availableGameweeks.map((option) => <option value={option.gameweek} key={option.gameweek}>GW{option.gameweek}</option>)}
        </select>
      </label>
    </div>
  );
}
