"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState, ReportViewer } from "@/components/ReportViewer";
import { ApiError, getLatestReport } from "@/src/lib/api";
import type { FullReportResponse } from "@/src/types/report";

export default function ReportsPage() {
  const [selectedReport, setSelectedReport] = useState<FullReportResponse | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      setError(null);
      try {
        const report = await getLatestReport();
        if (isMounted) setSelectedReport(report);
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof ApiError && caught.status === 404
            ? null
            : "The latest gameweek analysis is temporarily unavailable.");
        }
      } finally {
        if (isMounted) setIsLoadingReport(false);
      }
    }
    loadReport();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <PageShell
      title="Reports"
      eyebrow="Latest analysis"
      description="Review the latest published gameweek recommendations and supporting analysis."
    >
      {isLoadingReport ? <LoadingState label="Loading the latest report..." /> : null}
      {!isLoadingReport && error ? <ErrorState label={error} /> : null}
      {!isLoadingReport && !error && !selectedReport ? <EmptyState label="The latest gameweek analysis is temporarily unavailable." /> : null}
      {!isLoadingReport && !error && selectedReport ? <ReportViewer report={selectedReport} /> : null}
    </PageShell>
  );
}
