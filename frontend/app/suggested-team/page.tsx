"use client";

import { PageShell } from "@/components/PageShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ReportViewer";
import { SuggestedTeamPitch } from "@/components/SuggestedTeamPitch";
import { SuggestedTeamTable } from "@/components/SuggestedTeamTable";
import { useLatestReport } from "@/components/useLatestReport";

export default function SuggestedTeamPage() {
  const { data, error, loading } = useLatestReport();
  const reveals = data?.report.expert_team_reveals ?? [];
  const suggestedTeam = data?.report.suggested_team;
  const detailedPlayers = suggestedTeam?.players ?? suggestedTeam?.startingXi ?? [];

  return (
    <PageShell
      title="Suggested Team"
      eyebrow="Squad planner"
      description="Compare expert team reveals, armband choices, and the moves shaping this gameweek."
    >
      <div className="suggested-team-layout">
        <SuggestedTeamPitch formation={suggestedTeam?.formation} players={suggestedTeam?.startingXi} isLoading={loading} error={error} />
        <SuggestedTeamTable players={detailedPlayers} />
      </div>
      {loading ? <LoadingState label="Loading the latest team reveals..." /> : null}
      {error ? <ErrorState label={error} /> : null}
      {!loading && !error && !reveals.length && !suggestedTeam ? <EmptyState label="No expert team reveals are available in the latest report." /> : null}
      {reveals.length ? <section className="insight-grid" aria-label="Expert team reveals">{reveals.map((reveal, index) => (
        <article className={`insight-card ${index === 0 ? "featured" : ""}`} key={`${reveal.expert_name}-${index}`}>
          <span className="rank-badge">{index + 1}</span><h2>{reveal.expert_name}</h2><p>{reveal.summary}</p>
          <dl className="detail-grid"><div><dt>Captain</dt><dd>{reveal.captain ?? "—"}</dd></div><div><dt>Vice captain</dt><dd>{reveal.vice_captain ?? "—"}</dd></div><div><dt>Buying</dt><dd>{reveal.transfers_in?.join(", ") || "Hold"}</dd></div><div><dt>Selling</dt><dd>{reveal.transfers_out?.join(", ") || "None"}</dd></div></dl>
        </article>
      ))}</section> : null}
    </PageShell>
  );
}
