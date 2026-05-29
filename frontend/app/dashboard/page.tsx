"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState, ReportViewer } from "@/components/ReportViewer";
import { getErrorMessage } from "@/components/apiError";
import { getLatestReport, getReports } from "@/src/lib/api";
import type { FullReportResponse, ReportSummary } from "@/src/types/report";

export default function DashboardPage() {
  const [latestReport, setLatestReport] = useState<FullReportResponse | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      setIsLoading(true);
      setError(null);

      try {
        const [reportList, latest] = await Promise.all([getReports(), getLatestReport()]);
        if (isMounted) {
          setReports(reportList);
          setLatestReport(latest);
        }
      } catch (caught) {
        if (isMounted) {
          setError(getErrorMessage(caught));
          setLatestReport(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <PageShell
      title="Dashboard"
      description="Monitor the latest gameweek report, recent run history, and the headline FPL signals."
    >
      <section className="metric-strip" aria-label="Dashboard summary">
        <div className="metric">
          <span>Gameweek</span>
          <strong>{latestReport?.report.gameweek ? `GW${latestReport.report.gameweek}` : "--"}</strong>
        </div>
        <div className="metric">
          <span>Latest Run</span>
          <strong>{latestReport?.run_id ?? "None"}</strong>
        </div>
        <div className="metric">
          <span>Saved Reports</span>
          <strong>{reports.length}</strong>
        </div>
        <div className="metric">
          <span>Open Flags</span>
          <strong>{latestReport?.report.wait_for_news?.length ?? 0}</strong>
        </div>
      </section>
      {isLoading ? <LoadingState label="Loading the latest report..." /> : null}
      {!isLoading && error ? <ErrorState label={error} /> : null}
      {!isLoading && !error && !latestReport ? (
        <EmptyState label="No generated reports were found in data/reports." />
      ) : null}
      {!isLoading && !error && latestReport ? <ReportViewer report={latestReport} /> : null}
    </PageShell>
  );
}
