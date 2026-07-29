import * as React from "react";
import type { ExpertTeamReveal } from "../types";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type ExpertConsensusPanelProps = {
  reveals?: ExpertTeamReveal[];
  title?: string;
  subtitle?: string;
};

/** Shows a compact card per expert reveal (captain, VC, transfers, summary). */
export function ExpertConsensusPanel({ reveals, title = "Expert team reveals", subtitle }: ExpertConsensusPanelProps) {
  const items = reveals ?? [];
  return (
    <section className="kasifpl-section" aria-label={title}>
      <h2 className="kasifpl-section__title">{title}</h2>
      {subtitle ? <p className="kasifpl-section__subtitle">{subtitle}</p> : null}
      {items.length === 0 ? (
        <SectionUnavailableState message="No expert team reveals available for this gameweek." />
      ) : (
        <div className="kasifpl-grid kasifpl-grid--cols-2">
          {items.map((r, i) => (
            <article key={`${r.expert_name}-${i}`} className="kasifpl-card">
              <div className="kasifpl-card__header">
                <div>
                  <h3 className="kasifpl-card__title">{r.expert_name}</h3>
                  {(r.captain || r.vice_captain) ? (
                    <p className="kasifpl-card__subtitle">
                      {r.captain ? `C: ${r.captain}` : null}
                      {r.captain && r.vice_captain ? " · " : null}
                      {r.vice_captain ? `VC: ${r.vice_captain}` : null}
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="kasifpl-card__body">
                {r.summary ? <p>{r.summary}</p> : null}
                {(r.transfers_in && r.transfers_in.length) || (r.transfers_out && r.transfers_out.length) ? (
                  <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {r.transfers_out?.map((p, ix) => (
                      <span key={`out-${ix}`} className="kasifpl-chip kasifpl-chip--danger">Out: {p}</span>
                    ))}
                    {r.transfers_in?.map((p, ix) => (
                      <span key={`in-${ix}`} className="kasifpl-chip kasifpl-chip--strong">In: {p}</span>
                    ))}
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
