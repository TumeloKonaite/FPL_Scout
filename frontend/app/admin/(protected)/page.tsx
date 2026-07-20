"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { ErrorState, LoadingState } from "@/components/ReportViewer";
import { getErrorMessage } from "@/components/apiError";
import { generateReport, getPipelineStatus, pollPipelineRun, runPipeline } from "@/src/lib/api";
import type { PipelineRun } from "@/src/types/report";

function formatDate(value?: string) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function AdminDashboardPage() {
  const [gameweek, setGameweek] = useState("32");
  const [perExpertLimit, setPerExpertLimit] = useState("2");
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const status = await getPipelineStatus();
      setRun(status.latest_run ?? null);
      setIsRunning(status.status === "queued" || status.status === "pending" || status.status === "running");
    } catch (caught) {
      setError(getErrorMessage(caught));
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsRunning(true);
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const action = submitter instanceof HTMLButtonElement ? submitter.value : "pipeline";
    const input = { gameweek: Number(gameweek), per_expert_limit: Number(perExpertLimit), synthesis_enabled: true };
    try {
      const accepted = action === "report" ? await generateReport(input) : await runPipeline(input);
      setRun(accepted);
      const completed = await pollPipelineRun(accepted, { onUpdate: setRun });
      setRun(completed);
      if (completed.status === "failed") setError(completed.error || "Pipeline run failed.");
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setIsRunning(false);
      refresh();
    }
  }

  return (
    <PageShell title="Administration" eyebrow="Pipeline operations" description="Run analysis, generate reports, and inspect internal execution status.">
      <section className="runner-layout" aria-label="Administrator pipeline controls">
        <form className="form-panel" onSubmit={handleSubmit}>
          <h2>Manual execution</h2>
          <label><span>Gameweek</span><input min="1" max="38" onChange={(event) => setGameweek(event.target.value)} required type="number" value={gameweek} /></label>
          <label><span>Videos per expert</span><input min="1" onChange={(event) => setPerExpertLimit(event.target.value)} required type="number" value={perExpertLimit} /></label>
          <button className="primary-button" disabled={isRunning} name="action" type="submit" value="pipeline">{isRunning ? "Execution in progress..." : "Run pipeline"}</button>
          <button className="primary-button" disabled={isRunning} name="action" type="submit" value="report">Generate report</button>
          <button disabled={isRunning} onClick={refresh} type="button">Refresh status</button>
        </form>

        <div className="result-panel">
          <h2>Latest run status</h2>
          {isRunning ? <LoadingState label={`Pipeline is ${run?.status ?? "queued"}${run?.current_stage ? ` — ${run.current_stage}` : ""}.`} /> : null}
          {error ? <ErrorState label={error} /> : null}
          {!run ? <p className="empty-copy">No pipeline runs have been recorded.</p> : (
            <dl className="detail-grid">
              <div><dt>Run ID</dt><dd>{run.run_id}</dd></div>
              <div><dt>Status</dt><dd>{run.status}</dd></div>
              <div><dt>Current stage</dt><dd>{run.current_stage ?? "Not active"}</dd></div>
              <div><dt>Queued</dt><dd>{formatDate(run.created_at)}</dd></div>
              <div><dt>Started</dt><dd>{formatDate(run.started_at)}</dd></div>
              <div><dt>Completed</dt><dd>{formatDate(run.completed_at)}</dd></div>
              <div><dt>Duration</dt><dd>{run.duration_seconds == null ? "Not available" : `${run.duration_seconds.toFixed(1)} seconds`}</dd></div>
              {run.error ? <div><dt>Failure details</dt><dd>{run.error}</dd></div> : null}
              {run.result && typeof run.result === "object" ? Object.entries(run.result as Record<string, unknown>).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>) : null}
            </dl>
          )}
        </div>
      </section>
    </PageShell>
  );
}
