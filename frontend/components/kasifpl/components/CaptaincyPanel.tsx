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
          {shown.map((r, i) => {
            const isTopPick = i === 0;
            return (
              <article
                key={i}
                className={`kasifpl-card ${isTopPick ? "kasifpl-cap__card--top" : ""}`}
              >
                <div className="kasifpl-cap">
                  <div
                    className={`kasifpl-cap__rank ${isTopPick ? "kasifpl-cap__rank--1" : ""}`}
                    aria-hidden
                  >
                    {i + 1}
                  </div>
                  <div className="kasifpl-cap__body">
                    <span
                      className={`kasifpl-cap__badge ${
                        isTopPick ? "kasifpl-cap__badge--top" : "kasifpl-cap__badge--alt"
                      }`}
                    >
                      {isTopPick ? "★ Primary Captain" : "Alternative Option"}
                    </span>
                    <h3 className="kasifpl-decision__title">
                      {r.playerName || r.title}
                      {isTopPick ? <span className="kasifpl-sr-only"> (top pick)</span> : null}
                    </h3>
                    <div className="kasifpl-decision__player">
                      {r.club ? <span className="kasifpl-chip kasifpl-chip--muted">{r.club}</span> : null}
                      {r.opponent ? <span>vs {r.opponent}{r.venue ? ` (${r.venue})` : ""}</span> : null}
                      {r.viceCaptain ? <span className="kasifpl-chip">VC: {r.viceCaptain}</span> : null}
                    </div>
                  </div>
                  <ConsensusChip
                    consensus={r.consensus}
                    fallback={{ consensusCount: r.consensusCount, expertCount: r.expertCount }}
                  />
                </div>
                {r.rationale ? (
                  <p className={`kasifpl-cap__rationale ${!isTopPick ? "kasifpl-cap__rationale--alt" : ""}`}>
                    {r.rationale}
                  </p>
                ) : null}
                <RecommendationEvidence
                  recommendation={r}
                  showSources={false}
                  collapsibleAlternatives={true}
                />
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
