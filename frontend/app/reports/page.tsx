import { PageShell } from "@/components/PageShell";

export default function ReportsPage() {
  return (
    <PageShell
      title="Reports"
      description="Browse generated gameweek reports and inspect their source artifacts."
    >
      <section className="placeholder-grid" aria-label="Report placeholders">
        <div className="placeholder-card">
          <h2>Report Library</h2>
          <p>List saved reports from the FastAPI backend when the report endpoint is available.</p>
        </div>
        <div className="placeholder-card">
          <h2>Report Preview</h2>
          <p>Render markdown summaries, consensus notes, and supporting metadata.</p>
        </div>
        <div className="placeholder-card">
          <h2>Artifacts</h2>
          <p>Expose JSON outputs for discovery, expert analysis, aggregation, and final synthesis.</p>
        </div>
      </section>
    </PageShell>
  );
}
