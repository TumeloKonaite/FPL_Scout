"use client";

import Link from "next/link";
import { reportHref } from "@/lib/reports/reportHref";
import { seasonLabel } from "@/lib/reports/reportSelection";
import { useSelectedReport } from "@/components/useSelectedReport";
import { ApiErrorState, ReportUnavailableState } from "@/components/kasifpl";

export function HistoricalReportBadge() {
  return <span className="kasifpl-chip kasifpl-chip--moderate">Historical snapshot</span>;
}

export function MissingReportState() {
  const { selection, newestAvailable, availableSeasons } = useSelectedReport();
  const message = availableSeasons.length === 0
    ? "No published reports are available yet."
    : selection && selection.season && Number.isInteger(selection.gameweek)
    ? `No report is available for Gameweek ${selection.gameweek} of the ${seasonLabel(selection.season)} season.`
    : "The requested report selection is invalid or unavailable.";
  return <ReportUnavailableState message={message} action={newestAvailable ? <Link className="kasifpl-btn kasifpl-btn--primary" href={reportHref("/dashboard", newestAvailable)}>View the newest available report</Link> : undefined} />;
}

export function ReportErrorState() {
  const { retry } = useSelectedReport();
  return <ApiErrorState onRetry={retry} />;
}

export function MissingReportSection({ children }: { children: React.ReactNode }) {
  return <div className="kasifpl-state">{children}</div>;
}
