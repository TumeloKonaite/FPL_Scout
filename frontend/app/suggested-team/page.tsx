"use client";

import { PageShell } from "@/components/PageShell";
import { ErrorState } from "@/components/ReportViewer";
import { SuggestedTeamBench } from "@/components/SuggestedTeamBench";
import { SuggestedTeamPitch } from "@/components/SuggestedTeamPitch";
import { SuggestedTeamTable } from "@/components/SuggestedTeamTable";
import { normalizeSuggestedTeam } from "@/components/suggestedTeam";
import { useLatestReport } from "@/components/useLatestReport";

function SuggestedTeamSkeleton() {
  return <div className="suggested-team-skeleton" role="status"><span>Loading the latest suggested team…</span></div>;
}

function UnavailableState() {
  return (
    <section className="pitch-state suggested-team-unavailable">
      <div><h2>Suggested team not available yet</h2><p>The latest recommendations for this gameweek have not been published.<br />Please check back once the current report is available.</p></div>
    </section>
  );
}

export default function SuggestedTeamPage() {
  const { data, error, loading, unavailable } = useLatestReport();
  const team = normalizeSuggestedTeam(data?.report.suggested_team);
  const gameweek = data?.gameweek ?? data?.report.gameweek;

  return (
    <PageShell title="Suggested Team" eyebrow="Squad planner" description="The latest expert-recommended lineup for the current gameweek.">
      {loading ? <SuggestedTeamSkeleton /> : null}
      {!loading && error ? <ErrorState label={error} /> : null}
      {!loading && !error && unavailable ? <UnavailableState /> : null}
      {!loading && !error && !unavailable && data && !team ? (
        <section className="pitch-state" role="status"><div><h2>Suggested team data is incomplete</h2><p>The current report is available, but its suggested-team section has not been published yet.</p></div></section>
      ) : null}
      {!loading && !error && !unavailable && team ? (
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
