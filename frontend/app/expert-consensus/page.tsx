import { PageShell } from "@/components/PageShell";

export default function ExpertConsensusPage() {
  return (
    <PageShell
      title="Expert Consensus"
      description="Review agreement, disagreement, and emerging themes across tracked FPL experts."
    >
      <section className="placeholder-grid" aria-label="Expert consensus placeholders">
        <div className="placeholder-card">
          <h2>Consensus Themes</h2>
          <p>Surface repeated recommendations and shared strategic direction.</p>
        </div>
        <div className="placeholder-card">
          <h2>Disagreements</h2>
          <p>Highlight where experts split on picks, captaincy, transfers, or chip timing.</p>
        </div>
        <div className="placeholder-card">
          <h2>Source Coverage</h2>
          <p>Track which creator videos contributed to the latest analysis.</p>
        </div>
      </section>
    </PageShell>
  );
}
