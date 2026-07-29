"use client";

import * as React from "react";
import type { SuggestedPlayer } from "../types";
import { positionClass } from "./_shared";

export type PlayerTileProps = {
  player: SuggestedPlayer;
  isCaptain?: boolean;
  isViceCaptain?: boolean;
  onSelect?: (player: SuggestedPlayer) => void;
};

export function PlayerTile({ player, isCaptain, isViceCaptain, onSelect }: PlayerTileProps) {
  const captain = isCaptain ?? player.captain ?? false;
  const vice = isViceCaptain ?? player.viceCaptain ?? false;
  const shirtNumber = player.shirtNumber ?? player.number ?? null;
  const label = player.displayName || player.name;

  const title = [
    player.name,
    player.club || undefined,
    player.fixture || undefined,
  ].filter(Boolean).join(" — ");

  return (
    <button
      type="button"
      className={`kasifpl-player ${positionClass(player.position)}`}
      onClick={() => onSelect?.(player)}
      title={title}
      aria-label={`${label}${captain ? ", captain" : vice ? ", vice-captain" : ""}`}
    >
      <span className="kasifpl-player__shirt" aria-hidden>
        {shirtNumber ?? player.position}
      </span>
      <span className="kasifpl-player__name">{label}</span>
      {captain ? <span className="kasifpl-player__badge" aria-hidden>C</span> : null}
      {!captain && vice ? <span className="kasifpl-player__badge kasifpl-player__badge--vc" aria-hidden>V</span> : null}
    </button>
  );
}

export type PlayerDetailsPopoverProps = {
  player: SuggestedPlayer | null;
  onClose: () => void;
};

/** Modal popover with the player's support/statistics. Keyboard: Esc closes. */
export function PlayerDetailsPopover({ player, onClose }: PlayerDetailsPopoverProps) {
  React.useEffect(() => {
    if (!player) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [player, onClose]);

  if (!player) return null;

  const rows: Array<{ label: string; value: React.ReactNode }> = [];
  if (player.club) rows.push({ label: "Club", value: player.club });
  if (player.fixture) rows.push({ label: "Fixture", value: player.fixture });
  if (player.price != null) rows.push({ label: "Price", value: `£${player.price.toFixed(1)}m` });
  if (player.predictedPoints != null) rows.push({ label: "Predicted pts", value: player.predictedPoints.toFixed(1) });
  if (player.ownership != null) rows.push({ label: "Ownership", value: `${player.ownership.toFixed(1)}%` });
  if (player.expectedMinutes != null) rows.push({ label: "Expected mins", value: player.expectedMinutes.toFixed(0) });
  if (player.fixtureDifficulty != null) rows.push({ label: "FDR", value: player.fixtureDifficulty });

  const s = player.support;
  if (s) {
    rows.push({
      label: "Starter support",
      value: `${s.starterSupportCount}/${s.eligibleExpertCount} (${Math.round(s.starterSupportPercentage)}%)`,
    });
    if (s.captainSupportCount > 0) {
      rows.push({ label: "Captain support", value: `${s.captainSupportCount}/${s.eligibleExpertCount}` });
    }
    if (s.viceCaptainSupportCount > 0) {
      rows.push({ label: "Vice support", value: `${s.viceCaptainSupportCount}/${s.eligibleExpertCount}` });
    }
  } else if (player.expertSupportCount != null) {
    rows.push({ label: "Expert support", value: `${player.expertSupportCount}` });
  }

  return (
    <div
      className="kasifpl-popover-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`${player.name} details`}
      onClick={onClose}
    >
      <div className="kasifpl-popover" onClick={(e) => e.stopPropagation()}>
        <div className="kasifpl-popover__header">
          <div>
            <h3 className="kasifpl-popover__title">{player.displayName || player.name}</h3>
            <p className="kasifpl-popover__sub">
              {[player.position, player.club].filter(Boolean).join(" · ")}
            </p>
          </div>
          <button type="button" className="kasifpl-popover__close" aria-label="Close" onClick={onClose}>×</button>
        </div>
        {rows.length ? (
          <div className="kasifpl-popover__grid">
            {rows.map((row) => (
              <div key={row.label} className="kasifpl-popover__stat">
                <div className="kasifpl-popover__stat-label">{row.label}</div>
                <div className="kasifpl-popover__stat-value">{row.value}</div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: "var(--kasifpl-color-fg-muted)", fontSize: "0.875rem" }}>
            No additional statistics available for this player.
          </p>
        )}
      </div>
    </div>
  );
}
