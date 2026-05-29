import { PageShell } from "@/components/PageShell";

export default function PipelineRunnerPage() {
  return (
    <PageShell
      title="Pipeline Runner"
      description="Prepare controls for launching, monitoring, and reviewing report generation runs."
    >
      <section className="placeholder-grid" aria-label="Pipeline runner placeholders">
        <div className="placeholder-card">
          <h2>Run Configuration</h2>
          <p>Future controls will set gameweek, expert filters, output location, and synthesis options.</p>
        </div>
        <div className="placeholder-card">
          <h2>Execution Status</h2>
          <p>Show pipeline progress, completed stages, failures, and retry affordances.</p>
        </div>
        <div className="placeholder-card">
          <h2>Run Output</h2>
          <p>Link directly to generated reports and artifacts after a pipeline completes.</p>
        </div>
      </section>
    </PageShell>
  );
}
