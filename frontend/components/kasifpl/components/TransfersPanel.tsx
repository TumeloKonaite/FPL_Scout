import * as React from "react";
import type { FinalRecommendation } from "../types";
import { DecisionCard } from "./DecisionCard";
import { SectionUnavailableState } from "./SectionUnavailableState";
import { ConsensusChip } from "./_shared";

export type TransfersPanelProps = {
  transfers?: FinalRecommendation[];
  title?: string;
  subtitle?: string;
  /** When true, only shows a compact swap summary per recommendation. */
  compact?: boolean;
};

export function TransfersPanel({ transfers, title = "Transfer recommendations", subtitle, compact }: TransfersPanelProps) {
  const items = transfers ?? [];
  return (
    <section className="kasifpl-section" aria-label={title}>
      <h2 className="kasifpl-section__title">{title}</h2>
      {subtitle ? <p className="kasifpl-section__subtitle">{subtitle}</p> : null}
      {items.length === 0 ? (
        <SectionUnavailableState message="No transfer recommendations for this gameweek." />
      ) : compact ? (
        <div className="kasifpl-grid kasifpl-grid--cols-2">
          {items.map((r, i) => <TransferSwapRow key={i} recommendation={r} />)}
        </div>
      ) : (
        <div className="kasifpl-grid kasifpl-grid--cols-2">
          {items.map((r, i) => <DecisionCard key={i} recommendation={r} eyebrow="Transfer" />)}
        </div>
      )}
    </section>
  );
}

export function TransferSwapRow({ recommendation }: { recommendation: FinalRecommendation }) {
  const { playerIn, playerOut } = recommendation;
  return (
    <div className="kasifpl-transfer__swap" role="group" aria-label="Transfer swap">
      {playerOut ? <span className="kasifpl-transfer__out">{playerOut}</span> : <span className="kasifpl-chip kasifpl-chip--muted">Player out unavailable</span>}
      <span className="kasifpl-transfer__arrow" aria-hidden>→</span>
      {playerIn ? <span className="kasifpl-transfer__in">{playerIn}</span> : <span className="kasifpl-chip kasifpl-chip--muted">Player in unavailable</span>}
      <span style={{ marginLeft: "auto" }}>
        <ConsensusChip
          consensus={recommendation.consensus}
          fallback={{ consensusCount: recommendation.consensusCount, expertCount: recommendation.expertCount }}
        />
      </span>
    </div>
  );
}
