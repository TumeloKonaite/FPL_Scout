"use client";

import Link from "next/link";
import {
  CaptaincyPanel,
  OverviewBriefingFromReport,
  ReportLoadingState,
  SuggestedTeamPitch,
  TransfersPanel
} from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";
import { reportHref } from "@/lib/reports/reportHref";
import { seasonLabel } from "@/lib/reports/reportSelection";

export default function DashboardPage() {
  const {
    selection,
    report: selectedReport,
    error,
    isLoadingIndex,
    isLoadingReport,
    isMissingReport,
    isCurrentReport
  } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const report = selectedReport?.report;

  return (
    <PageShell
      title={isCurrentReport
        ? `Gameweek ${selectedReport?.gameweek ?? report?.gameweek ?? ""} briefing`
        : selection
          ? `Gameweek ${selection.gameweek} — ${seasonLabel(selection.season)}`
          : "Gameweek briefing"}
      eyebrow="Overview"
      description={isCurrentReport
        ? "The most important expert-backed decisions before the deadline."
        : "A read-only snapshot of the recommendations published for this historical gameweek."}
      action={!loading && selectedReport && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <ReportLoadingState label="Loading the selected gameweek briefing…" /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report ? (
        <>
          <OverviewBriefingFromReport report={report} />
          <div className="kasifpl-dashboard-split">
            <TransfersPanel
              compact
              transfers={report.transfers?.slice(0, 2)}
              title="Priority transfers"
              subtitle="The leading moves in the selected report."
            />
            <CaptaincyPanel
              captaincy={report.captaincy}
              limit={2}
              title="Captaincy comparison"
              subtitle="The top two recorded options, ranked by the report."
            />
          </div>
          <section className="kasifpl-section" aria-labelledby="overview-team-title">
            <div className="kasifpl-overview-section-heading">
              <div>
                <h2 className="kasifpl-section__title" id="overview-team-title">Suggested XI preview</h2>
                <p className="kasifpl-section__subtitle">Built only when the selected report contains a valid starting XI.</p>
              </div>
              <Link className="kasifpl-btn kasifpl-btn--primary" href={reportHref("/suggested-team", selection)}>
                View full team
              </Link>
            </div>
            <SuggestedTeamPitch team={report.suggested_team} interactive={false} />
          </section>
        </>
      ) : null}
    </PageShell>
  );
}
