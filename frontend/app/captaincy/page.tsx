import { PageShell } from "@/components/PageShell";

export default function CaptaincyPage() {
  return (
    <PageShell
      title="Captaincy"
      description="Compare captain and vice-captain options using consensus, fixtures, and risk context."
    >
      <section className="placeholder-grid" aria-label="Captaincy placeholders">
        <div className="placeholder-card">
          <h2>Captain Ranking</h2>
          <p>Show the weekly captaincy shortlist with confidence and ownership signals.</p>
        </div>
        <div className="placeholder-card">
          <h2>Expert Mentions</h2>
          <p>Aggregate creator recommendations and notable disagreement.</p>
        </div>
        <div className="placeholder-card">
          <h2>Risk Notes</h2>
          <p>Track minutes, injury, fixture, and form caveats before locking in the armband.</p>
        </div>
      </section>
    </PageShell>
  );
}
