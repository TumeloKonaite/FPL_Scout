import { PageShell } from "@/components/PageShell";

export default function HomePage() {
  return (
    <PageShell
      title="Dashboard"
      description="A working area for gameweek status, latest reports, and FPL decision signals."
    >
      <section className="metric-strip" aria-label="Dashboard summary">
        <div className="metric">
          <span>Active Gameweek</span>
          <strong>GW --</strong>
        </div>
        <div className="metric">
          <span>Reports</span>
          <strong>0</strong>
        </div>
        <div className="metric">
          <span>Experts Tracked</span>
          <strong>0</strong>
        </div>
        <div className="metric">
          <span>Pipeline Status</span>
          <strong>Idle</strong>
        </div>
      </section>
      <section className="placeholder-grid" aria-label="Dashboard placeholders">
        <div className="placeholder-card">
          <h2>Latest Report</h2>
          <p>Surface the most recent generated report, run metadata, and quick links once backend integration is added.</p>
        </div>
        <div className="placeholder-card">
          <h2>Decision Queue</h2>
          <p>Reserve space for captaincy, transfer, and suggested-team recommendations.</p>
        </div>
        <div className="placeholder-card">
          <h2>Expert Signals</h2>
          <p>Track consensus strength, disagreement, and notable creator updates.</p>
        </div>
      </section>
    </PageShell>
  );
}
