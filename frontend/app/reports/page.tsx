"use client";

import { PageShell } from "@/components/PageShell";
import { LoadingState, ReportViewer } from "@/components/ReportViewer";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";
import { seasonLabel } from "@/lib/reports/reportSelection";

export default function ReportsPage() {
  const { selection, report, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport, error } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;

  return (
    <PageShell
      title="Reports"
      eyebrow={isCurrentReport ? "Current analysis" : "Report archive"}
      description={selection ? `Review the published recommendations for Gameweek ${selection.gameweek} of ${seasonLabel(selection.season)}.` : "Review published gameweek recommendations and supporting analysis."}
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <LoadingState label="Loading the selected report..." /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report ? <ReportViewer report={report} historical={!isCurrentReport} /> : null}
    </PageShell>
  );
}
