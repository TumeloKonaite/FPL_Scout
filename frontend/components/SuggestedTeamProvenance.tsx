import { agreementLabel, type NormalizedSuggestedTeam } from "./suggestedTeam";

function generatedDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat(undefined, { dateStyle: "long" }).format(date);
}

export function SuggestedTeamProvenance({ team }: { team: NormalizedSuggestedTeam }) {
  if (team.constructionMethod === "legacy_snapshot" || !team.provenanceAvailable || !team.provenance) {
    return (
      <section className="data-card provenance-summary" aria-label="Suggested team provenance">
        <strong>Historical saved lineup</strong>
        <span>Original provenance unavailable</span>
        <span>{agreementLabel("insufficient")}</span>
      </section>
    );
  }

  const provenance = team.provenance;
  const isSingleReveal = team.constructionMethod === "single_reveal";
  return (
    <section className="data-card provenance-summary" aria-labelledby="team-provenance-title">
      <div>
        <span className="eyebrow">How this team was built</span>
        <h2 id="team-provenance-title">{isSingleReveal ? "Based on one expert reveal" : `Built from ${provenance.eligibleExpertCount} eligible experts`}</h2>
        <p>{isSingleReveal ? "Not a multi-expert consensus" : `${provenance.eligibleRevealCount} eligible reveals · ${agreementLabel(provenance.consensusStrength)} · Generated ${generatedDate(provenance.generatedAt)}`}</p>
      </div>
      <details>
        <summary>Provenance details</summary>
        <dl className="detail-grid">
          <div><dt>Contributing experts</dt><dd>{provenance.contributingExperts.map((expert) => expert.expertName).join(", ") || "None"}</dd></div>
          <div><dt>Eligible experts</dt><dd>{provenance.eligibleExpertCount}</dd></div>
          <div><dt>Eligible reveals</dt><dd>{provenance.eligibleRevealCount}</dd></div>
          <div><dt>Excluded reveals</dt><dd>{provenance.excludedRevealCount}</dd></div>
          <div><dt>Formation derivation</dt><dd>{provenance.formationDerivation.method.replaceAll("_", " ")} using {provenance.formationDerivation.positionSource.replaceAll("_", " ")}</dd></div>
          <div><dt>Generated</dt><dd>{generatedDate(provenance.generatedAt)}</dd></div>
          <div><dt>Expert agreement</dt><dd>{agreementLabel(provenance.consensusStrength)}</dd></div>
          <div><dt>Agreement basis</dt><dd>Median starter support: {provenance.consensusStrengthBasis.medianSupportPercentage == null ? "Unavailable" : `${provenance.consensusStrengthBasis.medianSupportPercentage}%`}</dd></div>
        </dl>
        {provenance.excludedReveals.length ? (
          <div>
            <h3>Excluded reveals</h3>
            <ul>{provenance.excludedReveals.map((reveal, index) => (
              <li key={`${reveal.revealId ?? "reveal"}-${index}`}>
                {reveal.expertName ?? reveal.expertId ?? reveal.sourceTitle ?? "Unknown reveal"}: {reveal.reasons.join(", ").replaceAll("_", " ")}
              </li>
            ))}</ul>
          </div>
        ) : null}
      </details>
    </section>
  );
}
