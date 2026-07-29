import * as React from "react";
import type { SuggestedPlayer, SuggestedTeam } from "../types";

export type SuggestedTeamConsensusPanelProps = {
  team: SuggestedTeam;
  historical?: boolean;
};

function readable(value?: string | null): string {
  return value ? value.replaceAll("_", " ") : "Unavailable";
}

function starters(team: SuggestedTeam): SuggestedPlayer[] {
  return team.startingXi
    ?? team.starters
    ?? team.players?.filter((player) => player.isStarter !== false)
    ?? [];
}

function selectedPlayer(team: SuggestedTeam, kind: "captain" | "viceCaptain"): SuggestedPlayer | undefined {
  const players = [...starters(team), ...(team.bench ?? [])];
  const id = kind === "captain" ? team.captainPlayerId : team.viceCaptainPlayerId;
  return players.find((player) => player.playerId === id)
    ?? players.find((player) => Boolean(player[kind]));
}

function SummaryMetric({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="kasifpl-consensus__metric"><dt>{label}</dt><dd>{value}</dd></div>;
}

function safeUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function SuggestedTeamConsensusPanel({ team, historical = false }: SuggestedTeamConsensusPanelProps) {
  const provenance = team.provenance;
  const captain = selectedPlayer(team, "captain");
  const viceCaptain = selectedPlayer(team, "viceCaptain");
  const captainVotes = captain?.support?.captainSupportCount ?? captain?.captainSupport ?? null;
  const viceVotes = viceCaptain?.support?.viceCaptainSupportCount ?? viceCaptain?.viceCaptainSupport ?? null;
  const contributors = provenance?.contributingExperts
    ?? team.contributingReveals?.map((reveal) => ({
      expertId: reveal.expertId,
      expertName: reveal.expertName,
      revealIds: reveal.sourceId ? [reveal.sourceId] : []
    }))
    ?? [];
  const contributingRevealCount = provenance?.contributingRevealCount
    ?? team.contributingRevealCount
    ?? team.contributingReveals?.length;
  const contributorCount = team.contributingExpertCount
    ?? provenance?.contributingExpertCount
    ?? (contributors.length || null);

  return (
    <aside className="kasifpl-consensus" aria-label="Suggested team consensus and provenance">
      <div>
        <p className="kasifpl-consensus__eyebrow">Consensus provenance</p>
        <h2>How this XI was built</h2>
      </div>

      {team.consensusStrength === "split" ? (
        <div className="kasifpl-consensus__split" role="status">
          <strong>Split consensus</strong>
          <p>This XI combines the highest-supported valid squad across the eligible experts. Several selections were backed by only one expert.</p>
        </div>
      ) : null}

      <dl className="kasifpl-consensus__metrics">
        <SummaryMetric label="Construction method" value={readable(team.constructionMethod ?? provenance?.constructionMethod)} />
        <SummaryMetric label="Consensus strength" value={readable(team.consensusStrength ?? provenance?.consensusStrength)} />
        <SummaryMetric label="Median XI support" value={provenance?.consensusStrengthBasis.medianSupportPercentage != null ? `${Math.round(provenance.consensusStrengthBasis.medianSupportPercentage)}%` : "Unavailable"} />
        <SummaryMetric label="Eligible experts" value={team.eligibleExpertCount ?? provenance?.eligibleExpertCount ?? "Unavailable"} />
        <SummaryMetric label="Eligible reveals" value={team.eligibleRevealCount ?? provenance?.eligibleRevealCount ?? "Unavailable"} />
        <SummaryMetric label="Contributing experts" value={contributorCount ?? "Unavailable"} />
        <SummaryMetric label="Formation" value={team.formation ?? provenance?.formationDerivation.formation ?? "Validated from XI"} />
        <SummaryMetric label="Position source" value={readable(provenance?.formationDerivation.positionSource)} />
        <SummaryMetric label="Historical status" value={historical || team.constructionMethod === "legacy_snapshot" ? "Historical snapshot" : "Current report"} />
      </dl>

      <section className="kasifpl-consensus__captaincy" aria-labelledby="team-captaincy-title">
        <h3 id="team-captaincy-title">Captaincy</h3>
        <div>
          <article>
            <span className="kasifpl-consensus__armband">C</span>
            <p><strong>{captain?.displayName ?? captain?.name ?? "Unavailable"}</strong><span>{captainVotes != null ? `${captainVotes} captain vote${captainVotes === 1 ? "" : "s"}` : "Vote count unavailable"}</span></p>
          </article>
          <article>
            <span className="kasifpl-consensus__armband kasifpl-consensus__armband--vice">VC</span>
            <p><strong>{viceCaptain?.displayName ?? viceCaptain?.name ?? "Unavailable"}</strong><span>{viceVotes != null ? `${viceVotes} vice-captain vote${viceVotes === 1 ? "" : "s"}` : "Vote count unavailable"}</span></p>
          </article>
        </div>
      </section>

      <section className="kasifpl-consensus__provenance" aria-labelledby="team-provenance-title">
        <h3 id="team-provenance-title">Contributors and methodology</h3>
        {contributors.length ? (
          <ul>
            {contributors.map((expert) => (
              <li key={expert.expertId}>
                <strong>{expert.expertName}</strong>
                <span>{expert.revealIds.length ? `${expert.revealIds.length} contributing reveal${expert.revealIds.length === 1 ? "" : "s"}` : "Contributing reveal recorded"}</span>
              </li>
            ))}
          </ul>
        ) : <p>Contributor names are unavailable for this snapshot.</p>}
        {team.contributingReveals?.length ? (
          <div className="kasifpl-consensus__reveals">
            <strong>Contributing reveals</strong>
            <ul>
              {team.contributingReveals.map((reveal, index) => {
                const href = safeUrl(reveal.sourceUrl);
                const label = reveal.sourceId || `Reveal ${index + 1}`;
                return (
                  <li key={`${reveal.expertId}-${reveal.sourceId ?? index}`}>
                    <span>{reveal.expertName}</span>
                    {href ? <a href={href} target="_blank" rel="noopener noreferrer">{label}</a> : <span>{label}</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
        <dl>
          <SummaryMetric label="Contributing reveals" value={contributingRevealCount ?? "Unavailable"} />
          <SummaryMetric label="Excluded reveals" value={provenance?.excludedRevealCount ?? "Unavailable"} />
          <SummaryMetric label="Formation derivation" value={readable(provenance?.formationDerivation.method)} />
          <SummaryMetric label="Authoritative catalogue" value={provenance ? (provenance.formationDerivation.authoritativeCataloguePositions ? "Yes" : "No") : "Unavailable"} />
        </dl>
      </section>

      {team.warnings?.length ? (
        <section className="kasifpl-consensus__warnings" aria-labelledby="team-warnings-title">
          <h3 id="team-warnings-title">Data warnings</h3>
          <ul>{team.warnings.map((warning) => <li key={warning}>{readable(warning)}</li>)}</ul>
        </section>
      ) : null}
    </aside>
  );
}
