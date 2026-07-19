"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ReportViewer";
import { Icon } from "@/components/Icons";
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
      eyebrow="Decision room"
      description="Your weekly intelligence briefing, distilled from the latest expert analysis."
      action={<Link className="text-button" href="/pipeline-runner">Generate report <Icon name="arrow" /></Link>}
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
      {!isLoading && !error && latestReport ? (
        <section className="dashboard-grid" aria-label="Latest briefing">
          <article className="briefing-card">
            <span className="eyebrow">Latest intelligence · GW{latestReport.report.gameweek ?? "—"}</span>
            <h2>{latestReport.report.conclusion || "Your gameweek briefing is ready."}</h2>
            <p>{latestReport.report.overview}</p>
            <div className="briefing-actions">
              <Link className="text-button" href="/reports">Read full report <Icon name="arrow" /></Link>
              <Link className="text-button secondary" href="/captaincy">Captain picks</Link>
            </div>
          </article>
          <aside className="side-card">
            <div className="card-heading"><h2>Key signals</h2><span>This gameweek</span></div>
            <div className="signal-list">
              <div className="signal-item"><span className="signal-icon"><Icon name="captain" /></span><div><strong>Captaincy</strong><span>{latestReport.report.captaincy?.[0]?.title ?? "No leading pick yet"}</span></div></div>
              <div className="signal-item"><span className="signal-icon"><Icon name="transfers" /></span><div><strong>Top transfer</strong><span>{latestReport.report.transfers?.[0]?.title ?? "No move recommended"}</span></div></div>
              <div className="signal-item"><span className="signal-icon"><Icon name="alert" /></span><div><strong>News watch</strong><span>{latestReport.report.wait_for_news?.[0] ?? "No urgent flags"}</span></div></div>
            </div>
          </aside>
        </section>
      ) : null}
    </PageShell>
  );
}
