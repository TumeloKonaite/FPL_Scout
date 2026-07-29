"use client";

import * as React from "react";
import type { SuggestedPlayer } from "../types";
import { positionClass } from "./_shared";

export type PlayerTileProps = {
  player: SuggestedPlayer;
  isCaptain?: boolean;
  isViceCaptain?: boolean;
  onSelect?: (player: SuggestedPlayer) => void;
  benchRole?: string;
};

function supportTone(player: SuggestedPlayer): "strong" | "moderate" | "limited" | "neutral" {
  const support = player.support;
  if (!support || support.eligibleExpertCount <= 0) return "neutral";
  const ratio = support.starterSupportCount / support.eligibleExpertCount;
  if (ratio === 1) return "strong";
  if (ratio >= 2 / 3) return "moderate";
  if (support.starterSupportCount > 0) return "limited";
  return "neutral";
}

function playerLabel(player: SuggestedPlayer): string {
  if (player.displayName?.trim()) return player.displayName.trim();
  const parts = player.name.trim().split(/\s+/);
  if (parts.length <= 1) return player.name;
  const surname = parts.at(-1) ?? player.name;
  return parts[0].endsWith(".") ? `${parts[0]} ${surname}` : surname;
}

export function PlayerTile({ player, isCaptain, isViceCaptain, onSelect, benchRole }: PlayerTileProps) {
  const captain = isCaptain ?? player.captain ?? false;
  const vice = isViceCaptain ?? player.viceCaptain ?? false;
  const label = playerLabel(player);
  const support = player.support;
  const supportText = support
    ? `${support.starterSupportCount} of ${support.eligibleExpertCount}`
    : player.expertSupportCount != null
      ? `${player.expertSupportCount} experts`
      : "Support unavailable";

  return (
    <button
      type="button"
      className={`kasifpl-player ${positionClass(player.position)} kasifpl-player--support-${supportTone(player)}`}
      onClick={() => onSelect?.(player)}
      title={[player.name, player.club, player.fixture].filter(Boolean).join(" — ")}
      aria-label={`${label}, ${supportText}${captain ? ", captain" : vice ? ", vice-captain" : ""}`}
    >
      <span className="kasifpl-player__topline">
        <span className="kasifpl-player__position">{player.club || player.position}</span>
        {player.shirtNumber != null ? <span className="kasifpl-player__shirt-number">#{player.shirtNumber}</span> : null}
      </span>
      <span className="kasifpl-player__name">{label}</span>
      <span className="kasifpl-player__support">{supportText}</span>
      {player.price != null ? <span className="kasifpl-player__price">£{player.price.toFixed(1)}m</span> : null}
      {benchRole ? <span className="kasifpl-player__bench-role">{benchRole}</span> : null}
      {captain ? <span className="kasifpl-player__badge" aria-label="Captain">C</span> : null}
      {!captain && vice ? <span className="kasifpl-player__badge kasifpl-player__badge--vc" aria-label="Vice-captain">VC</span> : null}
    </button>
  );
}

export type PlayerDetailsPopoverProps = {
  player: SuggestedPlayer | null;
  onClose: () => void;
};

export function PlayerDetailsPopover({ player, onClose }: PlayerDetailsPopoverProps) {
  React.useEffect(() => {
    if (!player) return;
    const handler = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [player, onClose]);

  if (!player) return null;

  const rows: Array<{ label: string; value: React.ReactNode }> = [
    { label: "Position", value: player.position }
  ];
  if (player.club) rows.push({ label: "Club", value: player.club });
  if (player.price != null) rows.push({ label: "Price", value: `£${player.price.toFixed(1)}m` });
  if (player.fixture) rows.push({ label: "Fixture", value: player.fixture });

  const support = player.support;
  if (support) {
    rows.push({ label: "Starter support", value: `${support.starterSupportCount} of ${support.eligibleExpertCount} (${Math.round(support.starterSupportPercentage)}%)` });
    rows.push({ label: "Squad support", value: `${support.squadSupportCount} of ${support.eligibleExpertCount}` });
    rows.push({ label: "Captain support", value: `${support.captainSupportCount} of ${support.eligibleExpertCount}` });
    rows.push({ label: "Vice-captain support", value: `${support.viceCaptainSupportCount} of ${support.eligibleExpertCount}` });
  } else if (player.expertSupportCount != null) {
    rows.push({ label: "Expert support", value: player.expertSupportCount });
  }

  const expertIds = support?.contributingExpertIds ?? player.contributingExpertIds ?? [];
  const revealIds = support?.contributingRevealIds ?? player.contributingRevealIds ?? [];

  return (
    <div className="kasifpl-popover-backdrop" role="dialog" aria-modal="true" aria-label={`${player.name} details`} onClick={onClose}>
      <div className="kasifpl-popover" onClick={(event) => event.stopPropagation()}>
        <div className="kasifpl-popover__header">
          <div>
            <h3 className="kasifpl-popover__title">{player.name}</h3>
            <p className="kasifpl-popover__sub">{[player.club, player.position].filter(Boolean).join(" · ")}</p>
          </div>
          <button type="button" className="kasifpl-popover__close" aria-label="Close" onClick={onClose}>×</button>
        </div>
        <div className="kasifpl-popover__grid">
          {rows.map((row) => (
            <div key={row.label} className="kasifpl-popover__stat">
              <div className="kasifpl-popover__stat-label">{row.label}</div>
              <div className="kasifpl-popover__stat-value">{row.value}</div>
            </div>
          ))}
        </div>
        <div className="kasifpl-popover__evidence">
          <strong>Supporting experts</strong>
          <p>{expertIds.length ? expertIds.join(", ") : "Expert identities unavailable"}</p>
        </div>
        <div className="kasifpl-popover__evidence">
          <strong>Source reveals</strong>
          <p>{revealIds.length ? revealIds.join(", ") : "Reveal identifiers unavailable"}</p>
        </div>
      </div>
    </div>
  );
}
