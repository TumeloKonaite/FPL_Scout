import { PageShell } from "@/components/PageShell";

export default function DashboardPage() {
  return (
    <PageShell
      title="Dashboard"
      description="Monitor the current gameweek, recent pipeline activity, and headline FPL signals."
    >
      <section className="metric-strip" aria-label="Dashboard summary">
        <div className="metric">
          <span>Gameweek</span>
          <strong>--</strong>
        </div>
        <div className="metric">
          <span>Latest Run</span>
          <strong>None</strong>
        </div>
        <div className="metric">
          <span>Videos Processed</span>
          <strong>0</strong>
        </div>
        <div className="metric">
          <span>Alerts</span>
          <strong>0</strong>
        </div>
      </section>
      <section className="placeholder-grid" aria-label="Dashboard modules">
        <div className="placeholder-card">
          <h2>Gameweek Overview</h2>
          <p>Upcoming deadlines, team health, and key context will live here.</p>
        </div>
        <div className="placeholder-card">
          <h2>Recent Activity</h2>
          <p>Show completed pipeline runs and report-generation history.</p>
        </div>
        <div className="placeholder-card">
          <h2>Priority Signals</h2>
          <p>Highlight the recommendations that need manager attention.</p>
        </div>
      </section>
    </PageShell>
  );
}
