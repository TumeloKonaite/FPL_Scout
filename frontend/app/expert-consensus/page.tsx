"use client";

import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ReportViewer";
import { useLatestReport } from "@/components/useLatestReport";

export default function ExpertConsensusPage() {
  const { data, error, loading } = useLatestReport();
  const report = data?.report;
  return (
    <PageShell
      title="Expert Consensus"
      eyebrow="Expert room"
      description="See where the expert panel aligns, where it splits, and what requires late news."
    >
      {loading ? <LoadingState label="Loading expert consensus..." /> : null}
      {error ? <ErrorState label={error} /> : null}
      {!loading && !error && !report ? <EmptyState label="No expert consensus report is available." /> : null}
      {report ? <section className="insight-grid" aria-label="Expert consensus">
        <article className="insight-card featured"><span className="rank-badge">✓</span><h2>Consensus themes</h2><p>{report.overview}</p></article>
        <article className="insight-card"><span className="rank-badge">≠</span><h2>Disagreements</h2>{report.disagreements?.length ? report.disagreements.map((item, index) => <p key={`${item.topic}-${index}`}><strong>{item.topic}:</strong> {item.summary}</p>) : <p>No major disagreements were identified.</p>}</article>
        <article className="insight-card"><span className="rank-badge">!</span><h2>Wait for news</h2>{report.wait_for_news?.length ? report.wait_for_news.map((item, index) => <p key={`${item}-${index}`}>{item}</p>) : <p>No late-news flags are open.</p>}</article>
      </section> : null}
    </PageShell>
  );
}
