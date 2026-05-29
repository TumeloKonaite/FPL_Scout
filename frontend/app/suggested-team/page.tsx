import { PageShell } from "@/components/PageShell";

export default function SuggestedTeamPage() {
  return (
    <PageShell
      title="Suggested Team"
      description="Plan the recommended starting XI, bench order, and squad notes for the active gameweek."
    >
      <section className="placeholder-grid" aria-label="Suggested team placeholders">
        <div className="placeholder-card">
          <h2>Starting XI</h2>
          <p>Display the recommended lineup and formation once team data is connected.</p>
        </div>
        <div className="placeholder-card">
          <h2>Bench Order</h2>
          <p>Reserve space for substitution priority and rotation risk notes.</p>
        </div>
        <div className="placeholder-card">
          <h2>Selection Rationale</h2>
          <p>Summarize why each key starter is included based on expert consensus.</p>
        </div>
      </section>
    </PageShell>
  );
}
