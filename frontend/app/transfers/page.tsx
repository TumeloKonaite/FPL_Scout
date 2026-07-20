"use client";

import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ReportViewer";
import { useLatestReport } from "@/components/useLatestReport";
import { RecommendationEvidence } from "@/components/RecommendationEvidence";

export default function TransfersPage() {
  const { data, error, loading } = useLatestReport();
  const moves = data?.report.transfers ?? [];
  return (
    <PageShell
      title="Transfers"
      eyebrow="Transfer radar"
      description="Prioritise this week’s moves with consensus strength and expert reasoning."
    >
      {loading ? <LoadingState label="Loading transfer recommendations..." /> : null}
      {error ? <ErrorState label={error} /> : null}
      {!loading && !error && !moves.length ? <EmptyState label="No transfer recommendations are available." /> : null}
      {moves.length ? <section className="insight-grid" aria-label="Transfer recommendations">{moves.map((move, index) => {
        return <article className={`insight-card ${index === 0 ? "featured" : ""}`} key={`${move.title}-${index}`}><span className="rank-badge">{index + 1}</span><h2>{move.title}</h2><p>{move.rationale}</p><RecommendationEvidence recommendation={move} /></article>;
      })}</section> : null}
    </PageShell>
  );
}
