"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState, ReportViewer } from "@/components/ReportViewer";
import { getErrorMessage } from "@/components/apiError";
import { getReport, getReports } from "@/src/lib/api";
import type { FullReportResponse, ReportSummary } from "@/src/types/report";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<FullReportResponse | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadReports() {
      setIsLoadingList(true);
      setError(null);

      try {
        const reportList = await getReports();
        if (!isMounted) {
          return;
        }
        setReports(reportList);
        const latest = reportList[reportList.length - 1];
        if (latest) {
          setSelectedRunId(latest.run_id);
        }
      } catch (caught) {
        if (isMounted) {
          setError(getErrorMessage(caught));
        }
      } finally {
        if (isMounted) {
          setIsLoadingList(false);
        }
      }
    }

    loadReports();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      setSelectedReport(null);
      return;
    }

    let isMounted = true;

    async function loadSelectedReport() {
      setIsLoadingReport(true);
      setError(null);

      try {
        const report = await getReport(selectedRunId as string);
        if (isMounted) {
          setSelectedReport(report);
        }
      } catch (caught) {
        if (isMounted) {
          setError(getErrorMessage(caught));
          setSelectedReport(null);
        }
      } finally {
        if (isMounted) {
          setIsLoadingReport(false);
        }
      }
    }

    loadSelectedReport();

    return () => {
      isMounted = false;
    };
  }, [selectedRunId]);

  return (
    <PageShell
      title="Reports"
      eyebrow="Report archive"
      description="Browse generated gameweek reports, choose older runs, and inspect every report section."
    >
      {isLoadingList ? <LoadingState label="Loading report history..." /> : null}
      {!isLoadingList && error ? <ErrorState label={error} /> : null}
      {!isLoadingList && !error && reports.length === 0 ? (
        <EmptyState label="No saved reports were found in data/reports." />
      ) : null}
      {!isLoadingList && !error && isLoadingReport ? (
        <LoadingState label="Loading selected report..." />
      ) : null}
      {!isLoadingList && !error && !isLoadingReport && selectedReport ? (
        <ReportViewer
          onSelectRun={setSelectedRunId}
          report={selectedReport}
          reports={reports}
          selectedRunId={selectedRunId ?? undefined}
        />
      ) : null}
    </PageShell>
  );
}
