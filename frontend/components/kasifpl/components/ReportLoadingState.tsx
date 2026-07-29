import * as React from "react";

export type ReportLoadingStateProps = {
  label?: string;
};

/** Skeleton placeholder shown while a report is loading. Server-safe. */
export function ReportLoadingState({ label = "Loading report…" }: ReportLoadingStateProps) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="kasifpl-sr-only">{label}</span>
      <div className="kasifpl-skeleton" style={{ height: 56, marginBottom: 16 }} />
      <div className="kasifpl-grid kasifpl-grid--cols-2">
        <div className="kasifpl-card">
          <div className="kasifpl-skeleton" style={{ height: 22, width: "40%", marginBottom: 12 }} />
          <div className="kasifpl-skeleton" style={{ height: 14, marginBottom: 6 }} />
          <div className="kasifpl-skeleton" style={{ height: 14, marginBottom: 6 }} />
          <div className="kasifpl-skeleton" style={{ height: 14, width: "70%" }} />
        </div>
        <div className="kasifpl-card">
          <div className="kasifpl-skeleton" style={{ height: 220 }} />
        </div>
      </div>
      <div style={{ height: 24 }} />
      <div className="kasifpl-grid kasifpl-grid--cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="kasifpl-card">
            <div className="kasifpl-skeleton" style={{ height: 20, width: "60%", marginBottom: 10 }} />
            <div className="kasifpl-skeleton" style={{ height: 14, marginBottom: 6 }} />
            <div className="kasifpl-skeleton" style={{ height: 14, width: "85%" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
