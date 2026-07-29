"use client";

import {
  ReportLoadingState,
  SectionUnavailableState,
  SuggestedTeamBench,
  SuggestedTeamConsensusPanel,
  SuggestedTeamPitch
} from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

export default function SuggestedTeamPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const team = report?.report.suggested_team;

  return (
    <PageShell
      title="Suggested Team"
      eyebrow="Squad planner"
      description="The selected report’s validated starting XI, bench, and player-level support."
      action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}
    >
      {loading ? <ReportLoadingState label="Loading the suggested team…" /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !team ? (
        <SectionUnavailableState title="Suggested team unavailable" message="This report does not contain suggested-team data." />
      ) : null}
      {!loading && !error && team ? (
        <div className="kasifpl-team-layout">
          <div className="kasifpl-team-layout__lineup">
            <SuggestedTeamPitch team={team} />
            <SuggestedTeamBench team={team} />
          </div>
          <SuggestedTeamConsensusPanel team={team} historical={!isCurrentReport} />
        </div>
      ) : null}
    </PageShell>
  );
}
