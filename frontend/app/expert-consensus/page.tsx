"use client";

import { PageShell } from "@/components/PageShell";
import { LoadingState } from "@/components/ReportViewer";
import { HistoricalReportBadge, MissingReportSection, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

export default function ExpertConsensusPage() {
  const { report: selectedReport, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const report = selectedReport?.report;
  const hasConsensus = Boolean(report && (report.overview?.trim() || report.disagreements?.length || report.wait_for_news?.length));
  return (
    <PageShell
      title="Expert Consensus"
      eyebrow="Expert room"
      description="See where the expert panel aligns, where it splits, and what requires late news."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <LoadingState label="Loading expert consensus..." /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !hasConsensus ? <MissingReportSection>No expert consensus data was available for this gameweek.</MissingReportSection> : null}
      {!loading && !error && report && hasConsensus ? <section className="insight-grid" aria-label="Expert consensus">
        <article className="insight-card featured"><span className="rank-badge">✓</span><h2>Consensus themes</h2><p>{report.overview}</p></article>
        <article className="insight-card"><span className="rank-badge">≠</span><h2>Disagreements</h2>{report.disagreements?.length ? report.disagreements.map((item, index) => <p key={`${item.topic}-${index}`}><strong>{item.topic}:</strong> {item.summary}</p>) : <p>No major disagreements were identified.</p>}</article>
        <article className="insight-card"><span className="rank-badge">!</span><h2>Wait for news</h2>{report.wait_for_news?.length ? report.wait_for_news.map((item, index) => <p key={`${item}-${index}`}>{item}</p>) : <p>No late-news flags are open.</p>}</article>
      </section> : null}
    </PageShell>
  );
}
