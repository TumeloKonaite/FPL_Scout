import * as React from "react";
import type { ExpertTeamReveal } from "../types";
import { SectionUnavailableState } from "./SectionUnavailableState";

export type ConsensusMatrixProps = {
  reveals?: ExpertTeamReveal[];
  title?: string;
};

/**
 * Renders a compact matrix of experts × their captain / vice / net transfers.
 * Purely presentational — no aggregation beyond what's supplied.
 */
export function ConsensusMatrix({ reveals, title = "Expert consensus matrix" }: ConsensusMatrixProps) {
  const items = reveals ?? [];
  if (items.length === 0) {
    return (
      <section className="kasifpl-section" aria-label={title}>
        <h2 className="kasifpl-section__title">{title}</h2>
        <SectionUnavailableState message="No expert data available for the matrix." />
      </section>
    );
  }
  return (
    <section className="kasifpl-section" aria-label={title}>
      <h2 className="kasifpl-section__title">{title}</h2>
      <div className="kasifpl-matrix">
        <table>
          <thead>
            <tr>
              <th scope="col">Expert</th>
              <th scope="col">Captain</th>
              <th scope="col">Vice</th>
              <th scope="col">In</th>
              <th scope="col">Out</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, i) => (
              <tr key={`${r.expert_name}-${i}`}>
                <th scope="row" style={{ fontWeight: 600 }}>{r.expert_name}</th>
                <td>{r.captain ?? "—"}</td>
                <td>{r.vice_captain ?? "—"}</td>
                <td>{r.transfers_in?.join(", ") || "—"}</td>
                <td>{r.transfers_out?.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
