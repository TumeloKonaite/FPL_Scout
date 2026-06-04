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
  assert.match(runner, /setError\(result\.error \|\| "Pipeline run failed\."\)/);
  assert.match(runner, /ErrorState label=\{error\}/);
  assert.match(runner, /LoadingState label="Pipeline is running\. This can take a while\.\.\."/);
  assert.match(runner, /No pipeline run has been started in this browser session\./);
});

test("API errors prefer backend detail messages", () => {
  const apiError = source("components/apiError.ts");

  assert.match(apiError, /error instanceof ApiError/);
  assert.match(apiError, /"detail" in detail/);
  assert.match(apiError, /return detail\.detail/);
  assert.match(apiError, /return `\$\{error\.status\} \$\{error\.statusText\}`/);
});
