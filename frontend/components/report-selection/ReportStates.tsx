"use client";

import Link from "next/link";
import { reportHref } from "@/lib/reports/reportHref";
import { seasonLabel } from "@/lib/reports/reportSelection";
import { useSelectedReport } from "@/components/useSelectedReport";

export function HistoricalReportBadge() {
  return <span className="historical-report-badge">Historical report</span>;
}

export function MissingReportState() {
  const { selection, newestAvailable, availableSeasons } = useSelectedReport();
  const message = availableSeasons.length === 0
    ? "No published reports are available yet."
    : selection && selection.season && Number.isInteger(selection.gameweek)
    ? `No report is available for Gameweek ${selection.gameweek} of the ${seasonLabel(selection.season)} season.`
    : "The requested report selection is invalid or unavailable.";
  return <div className="state-panel missing-report-state"><p>{message}</p>{newestAvailable ? <Link className="state-action" href={reportHref("/reports", newestAvailable)}>View the newest available report</Link> : null}</div>;
}

export function ReportErrorState() {
  const { retry } = useSelectedReport();
  return <div className="state-panel error-state" role="alert"><p>We could not load this report. Please try again.</p><button className="state-action" type="button" onClick={retry}>Try again</button></div>;
}

export function MissingReportSection({ children }: { children: React.ReactNode }) {
  return <div className="state-panel section-empty-state">{children}</div>;
}
