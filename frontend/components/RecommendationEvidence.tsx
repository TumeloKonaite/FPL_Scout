import type { FinalRecommendation, RecommendationSource } from "@/src/types/report";

const LABELS = {
  strong: "Strong consensus",
  moderate: "Moderate consensus",
  split: "Split opinion"
} as const;

function formatDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short"
  }).format(date);
}

function sourcePreview(sources: RecommendationSource[]): string | null {
  const names = [...new Set(sources.filter((source) => source.position === "support").map((source) => source.name))];
  if (!names.length) return null;
  const visible = names.slice(0, 3).join(", ");
  return names.length > 3 ? `${visible} +${names.length - 3}` : visible;
}

export function RecommendationEvidence({ recommendation, compact = false }: { recommendation: FinalRecommendation; compact?: boolean }) {
  const { consensus, freshness } = recommendation;
  const sources = recommendation.sources ?? [];
  const preview = sourcePreview(sources);
  if (!consensus && !sources.length && !freshness) return null;

  const supportText = consensus
    ? consensus.relevantExpertCount != null
      ? `Supported by ${consensus.supportCount} of ${consensus.relevantExpertCount} experts`
      : `${consensus.supportCount} expert mention${consensus.supportCount === 1 ? "" : "s"}`
    : null;

  return <div className={`recommendation-evidence ${compact ? "compact" : ""}`}>
    {consensus ? <div className="consensus-summary">
      <strong className={`consensus-label consensus-${consensus.label}`}>{LABELS[consensus.label]}</strong>
      <span>{supportText}</span>
      {consensus.oppositionCount > 0 ? <span>{consensus.oppositionCount} expert{consensus.oppositionCount === 1 ? "" : "s"} supported another view</span> : null}
    </div> : null}

    {recommendation.alternatives?.length ? <div className="alternative-list" aria-label="Competing recommendations">
      {recommendation.alternatives.slice(0, compact ? 2 : 4).map((alternative) => <span key={alternative.recommendation}>
        {alternative.recommendation}: {alternative.support_count} expert{alternative.support_count === 1 ? "" : "s"}
      </span>)}
    </div> : null}

    {preview ? <p className="source-preview"><strong>Sources:</strong> {preview}</p> : null}
    {!compact && sources.length ? <details className="source-details">
      <summary>View full source attribution</summary>
      <ul>{sources.map((source, index) => <li key={`${source.name}-${source.title}-${index}`}>
        <div><strong>{source.name}</strong> <span className={`source-position source-${source.position}`}>{source.position}</span></div>
        {source.title ? <span>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : source.title}</span> : null}
        {formatDate(source.publishedAt) ? <time dateTime={source.publishedAt ?? undefined}>{formatDate(source.publishedAt)}</time> : null}
      </li>)}</ul>
    </details> : null}
    {freshness ? <div className="freshness-meta">
      {freshness.sourceWindowHours != null ? <span>Source window: {freshness.sourceWindowHours} hours</span> : <span>Source publication window unavailable</span>}
      <span>Last updated: {formatDate(freshness.generatedAt) ?? "Unavailable"}</span>
    </div> : null}
  </div>;
}
