"use client";

import {
  ReportLoadingState,
  SectionUnavailableState,
  SuggestedTeamBench,
  SuggestedTeamPitch
} from "@/components/kasifpl";
import { PageShell } from "@/components/PageShell";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";
import { useSelectedReport } from "@/components/useSelectedReport";

function readable(value?: string | null): string {
  return value ? value.replaceAll("_", " ") : "Unavailable";
}

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
        <>
          <section className="kasifpl-team-summary" aria-label="Suggested team provenance">
            <span><strong>Method</strong>{readable(team.constructionMethod)}</span>
            <span><strong>Agreement</strong>{readable(team.consensusStrength)}</span>
            <span><strong>Eligible experts</strong>{team.eligibleExpertCount ?? "Unavailable"}</span>
            <span><strong>Formation</strong>{team.formation ?? "Validated from XI"}</span>
          </section>
          <SuggestedTeamPitch team={team} />
          <SuggestedTeamBench team={team} />
          {team.warnings?.length ? (
            <aside className="kasifpl-state" role="status">
              <h2 className="kasifpl-state__title">Team data notice</h2>
              <ul>{team.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            </aside>
          ) : null}
        </>
      ) : null}
    </PageShell>
  );
}
