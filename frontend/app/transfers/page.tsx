"use client";

import { PageShell } from "@/components/PageShell";
import { LoadingState } from "@/components/ReportViewer";
import { HistoricalReportBadge, MissingReportSection, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";
import { RecommendationEvidence } from "@/components/RecommendationEvidence";

export default function TransfersPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const moves = report?.report.transfers ?? [];
  return (
    <PageShell
      title="Transfers"
      eyebrow="Transfer radar"
      description="Prioritise this week’s moves with consensus strength and expert reasoning."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <LoadingState label="Loading transfer recommendations..." /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !moves.length ? <MissingReportSection>No transfer recommendations were recorded for this gameweek.</MissingReportSection> : null}
      {!loading && !error && moves.length ? <section className="insight-grid" aria-label="Transfer recommendations">{moves.map((move, index) => {
        return <article className={`insight-card ${index === 0 ? "featured" : ""}`} key={`${move.title}-${index}`}><span className="rank-badge">{index + 1}</span><h2>{move.title}</h2><p>{move.rationale}</p><RecommendationEvidence recommendation={move} /></article>;
      })}</section> : null}
    </PageShell>
  );
}
