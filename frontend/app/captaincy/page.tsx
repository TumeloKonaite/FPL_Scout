"use client";

import { PageShell } from "@/components/PageShell";
import { LoadingState } from "@/components/ReportViewer";
import { HistoricalReportBadge, MissingReportSection, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";
import { RecommendationEvidence } from "@/components/RecommendationEvidence";

export default function CaptaincyPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const picks = report?.report.captaincy ?? [];
  return (
    <PageShell
      title="Captaincy"
      eyebrow="Armband matrix"
      description="Compare captain options using expert agreement, source attribution, and late-news risk."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <LoadingState label="Loading captaincy intelligence..." /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !picks.length ? <MissingReportSection>No captaincy recommendations were recorded for this gameweek.</MissingReportSection> : null}
      {!loading && !error && picks.length ? <section className="insight-grid" aria-label="Captain ranking">{picks.map((pick, index) => {
        return <article className={`insight-card ${index === 0 ? "featured" : ""}`} key={`${pick.title}-${index}`}><span className="rank-badge">{index + 1}</span><h2>{pick.title}</h2><p>{pick.rationale}</p><RecommendationEvidence recommendation={pick} /></article>;
      })}</section> : null}
    </PageShell>
  );
}
