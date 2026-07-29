import * as React from "react";
import type { FinalRecommendation } from "../types";
import { ConsensusChip } from "./_shared";
import { RecommendationEvidence } from "./RecommendationEvidence";

export type DecisionCardProps = {
  recommendation: FinalRecommendation;
  /** Extra label such as "Captain" or "Transfer". Optional. */
  eyebrow?: string;
  /** Show the full evidence block below the card body. */
  showEvidence?: boolean;
  /** Optional right-side node (e.g., rank badge). */
  rightSlot?: React.ReactNode;
};

export function DecisionCard({ recommendation, eyebrow, showEvidence = true, rightSlot }: DecisionCardProps) {
  const r = recommendation;
  return (
    <article className="kasifpl-card">
      <div className="kasifpl-card__header">
        <div>
          {eyebrow ? <p className="kasifpl-card__subtitle">{eyebrow}</p> : null}
          <h3 className="kasifpl-decision__title">{r.title}</h3>
          {(r.playerName || r.club) ? (
            <div className="kasifpl-decision__player">
              {r.playerName ? <span className="kasifpl-decision__player-name">{r.playerName}</span> : null}
              {r.club ? <span>{r.club}</span> : null}
              {r.opponent ? <span>vs {r.opponent}{r.venue ? ` (${r.venue})` : ""}</span> : null}
              {r.price != null ? <span>£{r.price.toFixed(1)}m</span> : null}
              {r.position ? <span>{r.position}</span> : null}
            </div>
          ) : null}
        </div>
        <div className="kasifpl-decision__row">
          <ConsensusChip
            consensus={r.consensus}
            fallback={{ consensusCount: r.consensusCount, expertCount: r.expertCount }}
          />
          {rightSlot}
        </div>
      </div>
      <div className="kasifpl-card__body">
        <p className="kasifpl-decision__rationale">{r.rationale}</p>
        {showEvidence ? <RecommendationEvidence recommendation={r} /> : null}
      </div>
    </article>
  );
}
