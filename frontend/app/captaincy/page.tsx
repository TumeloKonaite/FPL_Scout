"use client";

import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ReportViewer";
import { useLatestReport } from "@/components/useLatestReport";

export default function CaptaincyPage() {
  const { data, error, loading } = useLatestReport();
  const picks = data?.report.captaincy ?? [];
  return (
    <PageShell
      title="Captaincy"
      eyebrow="Armband matrix"
      description="Compare captain options using expert confidence, rationale, and late-news risk."
    >
      {loading ? <LoadingState label="Loading captaincy intelligence..." /> : null}
      {error ? <ErrorState label={error} /> : null}
      {!loading && !error && !picks.length ? <EmptyState label="No captaincy recommendations are available." /> : null}
      {picks.length ? <section className="insight-grid" aria-label="Captain ranking">{picks.map((pick, index) => {
        const confidence = Math.round((pick.confidence ?? 0) * 100);
        return <article className={`insight-card ${index === 0 ? "featured" : ""}`} key={`${pick.title}-${index}`}><span className="rank-badge">{index + 1}</span><h2>{pick.title}</h2><p>{pick.rationale}</p>{pick.confidence != null ? <><div className="confidence-bar"><i style={{ width: `${confidence}%` }} /></div><p>{confidence}% expert confidence</p></> : null}</article>;
      })}</section> : null}
    </PageShell>
  );
}
