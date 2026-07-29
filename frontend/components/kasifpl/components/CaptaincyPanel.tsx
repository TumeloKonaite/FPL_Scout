import * as React from "react";
import type { FinalRecommendation } from "../types";
import { ConsensusChip } from "./_shared";
import { RecommendationEvidence } from "./RecommendationEvidence";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type CaptaincyPanelProps = {
  captaincy?: FinalRecommendation[];
  title?: string;
  subtitle?: string;
  /** Limit the number rendered (e.g. 2 for a briefing tile). */
  limit?: number;
};

export function CaptaincyPanel({ captaincy, title = "Captaincy", subtitle, limit }: CaptaincyPanelProps) {
  const items = (captaincy ?? []);
  const shown = typeof limit === "number" ? items.slice(0, limit) : items;

  return (
    <section className="kasifpl-section" aria-label={title}>
      <h2 className="kasifpl-section__title">{title}</h2>
      {subtitle ? <p className="kasifpl-section__subtitle">{subtitle}</p> : null}
      {shown.length === 0 ? (
        <SectionUnavailableState message="No captaincy picks are available for this gameweek." />
      ) : (
        <div className="kasifpl-grid kasifpl-grid--cols-2">
          {shown.map((r, i) => (
            <article key={i} className="kasifpl-card">
              <div className="kasifpl-cap">
                <div className={`kasifpl-cap__rank ${i === 0 ? "kasifpl-cap__rank--1" : ""}`} aria-hidden>{i + 1}</div>
                <div className="kasifpl-cap__body">
                  <h3 className="kasifpl-decision__title">
                    {r.playerName || r.title}
                    {i === 0 ? <span className="kasifpl-sr-only"> (top pick)</span> : null}
                  </h3>
                  <div className="kasifpl-decision__player">
                    {r.club ? <span>{r.club}</span> : null}
                    {r.opponent ? <span>vs {r.opponent}{r.venue ? ` (${r.venue})` : ""}</span> : null}
                    {r.viceCaptain ? <span>VC: {r.viceCaptain}</span> : null}
                  </div>
                </div>
                <ConsensusChip
                  consensus={r.consensus}
                  fallback={{ consensusCount: r.consensusCount, expertCount: r.expertCount }}
                />
              </div>
              <p style={{ marginTop: 12, fontSize: "0.9375rem", lineHeight: 1.55 }}>{r.rationale}</p>
              <RecommendationEvidence recommendation={r} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
