"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { getErrorMessage } from "@/components/apiError";
import { buildAdminPipelineInput, seasonValidationError } from "@/lib/admin/season";
import { failPipelineRun, getPipelineStatus, pollPipelineRun, runPipeline } from "@/src/lib/api";
import type { PipelineRun } from "@/src/types/report";

function formatDate(value?: string) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function AdminDashboardPage() {
  const [season, setSeason] = useState("");
  const [gameweek, setGameweek] = useState("32");
  const [perExpertLimit, setPerExpertLimit] = useState("2");
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seasonError, setSeasonError] = useState<string | null>(null);

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
    const validationError = seasonValidationError(season);
    setSeasonError(validationError);
    if (validationError) return;

    setError(null);
    setIsRunning(true);
    const input = buildAdminPipelineInput(season, gameweek, perExpertLimit);
    try {
      const accepted = await runPipeline(input);
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

  async function handleFailRun() {
    if (!run) return;
    setError(null);
    try {
      const failed = await failPipelineRun(run.run_id);
      setRun(failed);
      setIsRunning(false);
    } catch (caught) {
      setError(getErrorMessage(caught));
    }
  }

  return (
    <PageShell title="Administration" eyebrow="Pipeline operations" description="Run the report pipeline and inspect internal execution status.">
      <section className="runner-layout" aria-label="Administrator pipeline controls">
        <form className="form-panel" onSubmit={handleSubmit}>
          <h2>Manual execution</h2>
          <label>
            <span>Season</span>
            <input
              aria-describedby={seasonError ? "season-error" : undefined}
              aria-invalid={Boolean(seasonError)}
              maxLength={7}
              onBlur={() => setSeasonError(seasonValidationError(season))}
              onChange={(event) => {
                setSeason(event.target.value);
                if (seasonError) setSeasonError(seasonValidationError(event.target.value));
              }}
              onInvalid={(event) => {
                event.preventDefault();
                setSeasonError(seasonValidationError(season));
              }}
              pattern="[0-9]{4}-[0-9]{2}"
              placeholder="2025-26"
              required
              type="text"
              value={season}
            />
            {seasonError ? <small className="field-error" id="season-error" role="alert">{seasonError}</small> : null}
          </label>
          <label><span>Gameweek</span><input min="1" max="38" onChange={(event) => setGameweek(event.target.value)} required type="number" value={gameweek} /></label>
          <label><span>Videos per expert</span><input min="1" onChange={(event) => setPerExpertLimit(event.target.value)} required type="number" value={perExpertLimit} /></label>
          <button className="primary-button" disabled={isRunning} type="submit">{isRunning ? "Execution in progress..." : "Run pipeline"}</button>
          <button disabled={isRunning} onClick={refresh} type="button">Refresh status</button>
          {run && (run.status === "queued" || run.status === "running") ? (
            <button onClick={handleFailRun} type="button">Fail stuck run {run.run_id}</button>
          ) : null}
        </form>

        <div className="result-panel">
          <h2>Latest run status</h2>
          {isRunning ? <div aria-live="polite" className="state-panel loading-state">Pipeline is {run?.status ?? "queued"}{run?.current_stage ? ` — ${run.current_stage}` : ""}.</div> : null}
          {error ? <div className="state-panel error-state" role="alert">{error}</div> : null}
          {!run ? <p className="empty-copy">No pipeline runs have been recorded.</p> : (
            <dl className="detail-grid">
              <div><dt>Run ID</dt><dd>{run.run_id}</dd></div>
              <div><dt>Status</dt><dd>{run.status}</dd></div>
              <div><dt>Current stage</dt><dd>{run.current_stage ?? "Not active"}</dd></div>
              <div><dt>Queued</dt><dd>{formatDate(run.created_at)}</dd></div>
              <div><dt>Started</dt><dd>{formatDate(run.started_at)}</dd></div>
              <div><dt>Last heartbeat</dt><dd>{formatDate(run.heartbeat_at)}</dd></div>
              <div><dt>Lease expires</dt><dd>{formatDate(run.lease_expires_at)}</dd></div>
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
