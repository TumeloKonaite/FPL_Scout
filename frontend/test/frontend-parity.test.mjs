import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import test from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));

function source(path) {
  return readFileSync(join(root, path), "utf8");
}

test("dashboard loads the latest report and handles loading, empty, and error states", () => {
  const dashboard = source("app/dashboard/page.tsx");

  assert.match(dashboard, /getLatestReport\(\)/);
  assert.match(dashboard, /getReports\(\)/);
  assert.match(dashboard, /LoadingState label="Loading the latest report\.\.\."/);
  assert.match(dashboard, /EmptyState label="No generated reports were found in data\/reports\."/);
  assert.match(dashboard, /ErrorState label=\{error\}/);
});

test("reports page supports historical report selection", () => {
  const reportsPage = source("app/reports/page.tsx");

  assert.match(reportsPage, /getReports\(\)/);
  assert.match(reportsPage, /getReport\(selectedRunId as string\)/);
  assert.match(reportsPage, /onSelectRun=\{setSelectedRunId\}/);
  assert.match(reportsPage, /selectedRunId=\{selectedRunId \?\? undefined\}/);
  assert.match(reportsPage, /LoadingState label="Loading selected report\.\.\."/);
});

test("report viewer renders every final report section", () => {
  const viewer = source("components/ReportViewer.tsx");
  const expectedSections = [
    "Overview",
    "Transfers",
    "Captaincy",
    "Chip Strategy",
    "Fixture Notes",
    "Disagreements",
    "Conditional Advice",
    "Wait For News",
    "Expert Team Reveals",
    "Conclusion"
  ];

  for (const section of expectedSections) {
    assert.match(viewer, new RegExp(`<h2>${section}</h2>`));
  }
});

test("pipeline runner triggers backend runs and surfaces failures", () => {
  const runner = source("app/pipeline-runner/page.tsx");

  assert.match(runner, /runPipeline\(inputData\)/);
  assert.match(runner, /pollPipelineRun\(accepted, \{ onUpdate: setPipelineRun \}\)/);
  assert.match(runner, /setError\(result\.error \|\| "Pipeline run failed\."\)/);
  assert.match(runner, /ErrorState label=\{error\}/);
  assert.match(runner, /pipelineRun\?\.status \?\? "pending"/);
  assert.match(runner, /"Retry Pipeline"/);
  assert.match(runner, /No pipeline run has been started in this browser session\./);
});

test("API errors prefer backend detail messages", () => {
  const apiError = source("components/apiError.ts");

  assert.match(apiError, /error instanceof ApiError/);
  assert.match(apiError, /"detail" in detail/);
  assert.match(apiError, /return detail\.detail/);
  assert.match(apiError, /return `\$\{error\.status\} \$\{error\.statusText\}`/);
});

test("backend proxy injects mutation authentication server-side", () => {
  const nextConfig = source("next.config.ts");
  const route = source("app/backend/[...path]/route.ts");

  assert.match(nextConfig, /output:\s*"standalone"/);
  assert.match(route, /process\.env\.API_PROXY_TARGET/);
  assert.match(route, /process\.env\.PIPELINE_API_TOKEN/);
  assert.match(route, /headers\.set\("authorization", `Bearer/);
  assert.doesNotMatch(source("src/lib/api.ts"), /PIPELINE_API_TOKEN/);
  assert.doesNotMatch(source("src/lib/api.ts"), /NEXT_PUBLIC_/);
});

test("polling stops on terminal states and has retry and timeout limits", () => {
  const api = source("src/lib/api.ts");

  assert.match(api, /current\.status === "pending" \|\| current\.status === "running"/);
  assert.match(api, /maxConsecutiveErrors \?\? 3/);
  assert.match(api, /Date\.now\(\) >= deadline/);
  assert.match(api, /current = await getPipelineRun\(current\.run_id\)/);
});
