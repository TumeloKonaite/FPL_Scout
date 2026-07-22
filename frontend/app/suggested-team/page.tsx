"use client";

import { PageShell } from "@/components/PageShell";
import { SuggestedTeamBench } from "@/components/SuggestedTeamBench";
import { SuggestedTeamPitch } from "@/components/SuggestedTeamPitch";
import { SuggestedTeamTable } from "@/components/SuggestedTeamTable";
import { normalizeSuggestedTeam } from "@/components/suggestedTeam";
import { useSelectedReport } from "@/components/useSelectedReport";
import { HistoricalReportBadge, MissingReportState, ReportErrorState } from "@/components/report-selection/ReportStates";

function SuggestedTeamSkeleton() {
  return <div className="suggested-team-skeleton" role="status"><span>Loading the latest suggested team…</span></div>;
}

function UnavailableState() {
  return (
    <section className="pitch-state suggested-team-unavailable">
      <div><h2>Suggested team unavailable</h2><p>No recommended starting XI was generated for this gameweek.</p></div>
    </section>
  );
}

export default function SuggestedTeamPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const team = normalizeSuggestedTeam(report?.report.suggested_team);
  const gameweek = report?.gameweek ?? report?.report.gameweek;

  return (
    <PageShell title="Suggested Team" eyebrow="Squad planner" description="The expert-recommended lineup saved with the selected gameweek report." action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}>
      {loading ? <SuggestedTeamSkeleton /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !team ? <UnavailableState /> : null}
      {!loading && !error && team ? (
        <div className="suggested-team-layout">
          <SuggestedTeamPitch team={team} gameweek={gameweek} />
          {team.warnings.length ? <aside className="team-data-warning" role="status"><strong>Team data notice</strong><ul>{team.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></aside> : null}
          <SuggestedTeamBench team={team} />
          <SuggestedTeamTable players={team.allPlayers} />
        </div>
      ) : null}
    </PageShell>
  );
}
