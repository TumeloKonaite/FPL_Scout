"use client";

import { FormEvent, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { ErrorState, LoadingState } from "@/components/ReportViewer";
import { getErrorMessage } from "@/components/apiError";
import { runPipeline } from "@/src/lib/api";
import type { PipelineRun } from "@/src/types/report";

export default function PipelineRunnerPage() {
  const [gameweek, setGameweek] = useState("32");
  const [perExpertLimit, setPerExpertLimit] = useState("2");
  const [expertName, setExpertName] = useState("");
  const [expertCount, setExpertCount] = useState("");
  const [synthesisEnabled, setSynthesisEnabled] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pipelineRun, setPipelineRun] = useState<PipelineRun | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsRunning(true);
    setError(null);
    setPipelineRun(null);

    const inputData: Record<string, unknown> = {
      gameweek: Number(gameweek),
      per_expert_limit: Number(perExpertLimit),
      synthesis_enabled: synthesisEnabled
    };

    if (expertName.trim()) {
      inputData.expert_name = expertName.trim();
    }

    if (expertCount.trim()) {
      inputData.expert_count = Number(expertCount);
    }

    try {
      const result = await runPipeline(inputData);
      setPipelineRun(result);
      if (result.status === "failed") {
        setError(result.error || "Pipeline run failed.");
      }
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <PageShell
      title="Pipeline Runner"
      description="Launch the FPL reporting pipeline from the browser and review the run result."
    >
      <section className="runner-layout" aria-label="Pipeline runner">
        <form className="form-panel" onSubmit={handleSubmit}>
          <label>
            <span>Gameweek</span>
            <input
              min="1"
              onChange={(event) => setGameweek(event.target.value)}
              required
              type="number"
              value={gameweek}
            />
          </label>
          <label>
            <span>Videos per expert</span>
            <input
              min="1"
              onChange={(event) => setPerExpertLimit(event.target.value)}
              required
              type="number"
              value={perExpertLimit}
            />
          </label>
          <label>
            <span>Expert override</span>
            <input
              onChange={(event) => setExpertName(event.target.value)}
              placeholder="Optional"
              type="text"
              value={expertName}
            />
          </label>
          <label>
            <span>Expert count</span>
            <input
              min="1"
              onChange={(event) => setExpertCount(event.target.value)}
              placeholder="Optional"
              type="number"
              value={expertCount}
            />
          </label>
          <label className="checkbox-row">
            <input
              checked={synthesisEnabled}
              onChange={(event) => setSynthesisEnabled(event.target.checked)}
              type="checkbox"
            />
            <span>Enable final synthesis</span>
          </label>
          <button className="primary-button" disabled={isRunning} type="submit">
            {isRunning ? "Running..." : "Run Pipeline"}
          </button>
        </form>

        <div className="result-panel">
          <h2>Execution Status</h2>
          {isRunning ? <LoadingState label="Pipeline is running. This can take a while..." /> : null}
          {error ? <ErrorState label={error} /> : null}
          {!isRunning && !error && !pipelineRun ? (
            <p className="empty-copy">No pipeline run has been started in this browser session.</p>
          ) : null}
          {pipelineRun ? (
            <dl className="detail-grid">
              <div>
                <dt>Run ID</dt>
                <dd>{pipelineRun.run_id}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{pipelineRun.status}</dd>
              </div>
              {pipelineRun.result && typeof pipelineRun.result === "object" ? (
                Object.entries(pipelineRun.result as Record<string, unknown>).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replaceAll("_", " ")}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))
              ) : null}
            </dl>
          ) : null}
        </div>
      </section>
    </PageShell>
  );
}
