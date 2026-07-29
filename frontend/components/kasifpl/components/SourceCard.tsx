import * as React from "react";
import type { RecommendationSource } from "../types";
import { formatShortDate } from "./_shared";

export type SourceCardProps = {
  source: RecommendationSource;
};

const POSITION_LABEL: Record<RecommendationSource["position"], string> = {
  support: "Supports",
  oppose: "Opposes",
  alternative: "Alternative",
  mention: "Mentions",
};

export function SourceCard({ source }: SourceCardProps) {
  const hasValidUrl = typeof source.url === "string" && /^https?:\/\//i.test(source.url);
  const positionClass = `kasifpl-source__position kasifpl-source__position--${source.position}`;

  const content = (
    <>
      <div className="kasifpl-source__body">
        <div className="kasifpl-source__name">{source.name}</div>
        {source.title ? <div className="kasifpl-source__title">{source.title}</div> : null}
        <div className="kasifpl-source__meta">
          <span className={positionClass}>{POSITION_LABEL[source.position]}</span>
          {source.publishedAt ? (
            <span className="kasifpl-source__date">{formatShortDate(source.publishedAt)}</span>
          ) : null}
        </div>
      </div>
    </>
  );

  if (hasValidUrl) {
    return (
      <a
        href={source.url as string}
        className="kasifpl-source"
        target="_blank"
        rel="noopener noreferrer"
      >
        {content}
      </a>
    );
  }
  return <div className="kasifpl-source">{content}</div>;
}
