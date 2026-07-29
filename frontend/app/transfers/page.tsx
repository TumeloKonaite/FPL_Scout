"use client";

import { PageShell } from "@/components/PageShell";
import { ReportLoadingState, TransfersPanel } from "@/components/kasifpl";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

export default function TransfersPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  return (
    <PageShell
      title="Transfers"
      eyebrow="Transfer radar"
      description="Prioritise this week’s moves using the consensus and source evidence saved with the report."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <ReportLoadingState label="Loading transfer recommendations…" /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report ? (
        <TransfersPanel
          transfers={report.report.transfers}
          subtitle="Missing price, fixture, or evidence fields are left unavailable rather than inferred."
        />
      ) : null}
    </PageShell>
  );
}
