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

function UnavailableState({ reason }: { reason?: string | null }) {
  return (
    <section className="pitch-state suggested-team-unavailable">
      <div><h2>Consensus XI unavailable</h2><p>{reason ? reason.replaceAll("_", " ") : "No vote-based consensus squad was generated for this gameweek."}</p></div>
    </section>
  );
}

export default function SuggestedTeamPage() {
  const { report, error, isLoadingIndex, isLoadingReport, isMissingReport, isCurrentReport } = useSelectedReport();
  const loading = isLoadingIndex || isLoadingReport;
  const suggestedTeam = report?.report.suggested_team;
  const team = suggestedTeam?.constructionStatus === "consensus" ? normalizeSuggestedTeam(suggestedTeam) : null;
  const gameweek = report?.gameweek ?? report?.report.gameweek;

  return (
    <PageShell title="Suggested Team" eyebrow="Squad planner" description="The expert-recommended lineup saved with the selected gameweek report." action={!loading && report && !isCurrentReport ? <HistoricalReportBadge /> : undefined}>
      {loading ? <SuggestedTeamSkeleton /> : null}
      {!loading && error ? <ReportErrorState /> : null}
      {!loading && !error && isMissingReport ? <MissingReportState /> : null}
      {!loading && !error && report && !team ? <UnavailableState reason={suggestedTeam?.failureReason} /> : null}
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
