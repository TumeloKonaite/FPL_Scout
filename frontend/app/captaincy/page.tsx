"use client";

import { CaptaincyPanel, ReportLoadingState } from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

export default function CaptaincyPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  return (
    <PageShell
      title="Captaincy"
      eyebrow="Armband matrix"
      description="Compare captain options without treating mentions or missing evidence as expert votes."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <ReportLoadingState label="Loading captaincy intelligence…" /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report ? (
        <CaptaincyPanel
          captaincy={report.report.captaincy}
          title="Captaincy comparison"
          subtitle="Candidates are shown in the order stored by the selected report; support counts come from its consensus fields."
        />
      ) : null}
    </PageShell>
  );
}
