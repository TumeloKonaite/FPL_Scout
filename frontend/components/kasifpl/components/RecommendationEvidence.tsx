import * as React from "react";
import type { FinalRecommendation, RecommendationConsensus } from "../types";
import { SourceCard } from "./SourceCard";
import { consensusLabel, formatShortDate } from "./_shared";

export type RecommendationEvidenceProps = {
  recommendation: FinalRecommendation;
  showSources?: boolean;
};

function pct(c?: RecommendationConsensus | null): number | null {
  if (!c) return null;
  if (c.supportRatio != null && !Number.isNaN(c.supportRatio)) return Math.max(0, Math.min(1, c.supportRatio));
  if (c.relevantExpertCount && c.relevantExpertCount > 0) {
    return Math.max(0, Math.min(1, c.supportCount / c.relevantExpertCount));
  }
  return null;
}

export function RecommendationEvidence({ recommendation, showSources = true }: RecommendationEvidenceProps) {
  const c = recommendation.consensus ?? null;
  const support = c?.supportCount ?? recommendation.consensusCount ?? null;
  const total = c?.relevantExpertCount ?? recommendation.expertCount ?? null;
  const opposition = c?.oppositionCount ?? null;
  const mentions = c?.mentionCount ?? null;
  const ratio = pct(c);

  const alternatives = recommendation.alternatives ?? [];
  const sources = recommendation.sources ?? [];
  const freshness = recommendation.freshness ?? null;

  return (
    <div className="kasifpl-evidence" aria-label="Recommendation evidence">
      <div className="kasifpl-evidence__row">
        <span className="kasifpl-evidence__label">{consensusLabel(c?.label)}</span>
        {ratio != null ? (
          <div className="kasifpl-evidence__bar" role="img" aria-label={`${Math.round(ratio * 100)}% support`}>
            <div className="kasifpl-evidence__bar-fill" style={{ width: `${Math.round(ratio * 100)}%` }} />
          </div>
        ) : null}
        {support != null ? (
          <span className="kasifpl-chip kasifpl-chip--strong">
            {support}{total != null ? `/${total}` : ""} support
          </span>
        ) : null}
        {opposition != null && opposition > 0 ? (
          <span className="kasifpl-chip kasifpl-chip--danger">{opposition} oppose</span>
        ) : null}
        {mentions != null && mentions > 0 ? (
          <span className="kasifpl-chip kasifpl-chip--muted">{mentions} mention{mentions === 1 ? "" : "s"}</span>
        ) : null}
      </div>

      {recommendation.confidence != null ? (
        <div className="kasifpl-evidence__row">
          <span className="kasifpl-evidence__label">Model confidence</span>
          <span className="kasifpl-chip">{Math.round(recommendation.confidence * 100)}%</span>
          <span style={{ fontSize: "0.75rem", color: "var(--kasifpl-color-fg-subtle)" }}>
            Distinct from expert consensus.
          </span>
        </div>
      ) : null}

      {freshness ? (
        <div className="kasifpl-evidence__row">
          <span className="kasifpl-evidence__label">Freshness</span>
          <span className="kasifpl-chip kasifpl-chip--muted">
            Generated {formatShortDate(freshness.generatedAt)}
          </span>
          {freshness.newestSourceAt ? (
            <span className="kasifpl-chip kasifpl-chip--muted">Newest source {formatShortDate(freshness.newestSourceAt)}</span>
          ) : null}
          {freshness.sourceWindowHours != null ? (
            <span className="kasifpl-chip kasifpl-chip--muted">Window {freshness.sourceWindowHours}h</span>
          ) : null}
        </div>
      ) : null}

      {alternatives.length ? (
        <div>
          <div className="kasifpl-evidence__label" style={{ marginBottom: 6 }}>Alternatives</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {alternatives.map((a, i) => (
              <div key={i} className="kasifpl-transfer__swap">
                <span style={{ fontWeight: 600 }}>{a.recommendation}</span>
                <span className="kasifpl-chip">{a.support_count} support</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {showSources && sources.length ? (
        <div className="kasifpl-evidence__sources">
          <div className="kasifpl-evidence__label">Sources</div>
          {sources.map((s, i) => <SourceCard key={i} source={s} />)}
        </div>
      ) : null}
    </div>
  );
}
