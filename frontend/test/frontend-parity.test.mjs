import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import test from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));

function source(path) {
  return readFileSync(join(root, path), "utf8");
}

test("dashboard presents a read-only gameweek summary with resilient states", () => {
  const dashboard = source("app/dashboard/page.tsx");

  assert.match(dashboard, /useSelectedReport\(\)/);
  assert.doesNotMatch(dashboard, /getLatestReport\(\)/);
  assert.doesNotMatch(dashboard, /getReports\(\)/);
  assert.match(dashboard, /<DashboardSkeleton \/>/);
  assert.match(dashboard, /<MissingReportState \/>/);
  assert.match(dashboard, /<ReportErrorState \/>/);
  assert.match(dashboard, /isCurrentReport \? `This Gameweek\$\{gameweekLabel\}`/);
  assert.match(dashboard, /Gameweek \$\{report\.gameweek\} deadline/);
  assert.match(dashboard, /Last updated time unavailable/);
  assert.match(dashboard, />Top Captain</);
  assert.match(dashboard, />Top Transfer</);
  assert.match(dashboard, />Key Risk</);
  assert.match(dashboard, />Your Gameweek Action Plan</);
  assert.match(dashboard, />Consensus XI/);
  assert.doesNotMatch(dashboard, /Generate report/);
});

test("reports page renders the URL-selected public report", () => {
  const reportsPage = source("app/reports/page.tsx");

  assert.match(reportsPage, /useSelectedReport\(\)/);
  assert.doesNotMatch(reportsPage, /getLatestReport\(\)/);
  assert.doesNotMatch(reportsPage, /getReports\(\)/);
  assert.doesNotMatch(reportsPage, /selectedRunId/);
  assert.match(reportsPage, /<MissingReportState \/>/);
  assert.match(reportsPage, /historical=\{!isCurrentReport\}/);
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

test("recommendations show evidence without generic confidence percentages", () => {
  const evidence = source("components/RecommendationEvidence.tsx");
  const captaincy = source("app/captaincy/page.tsx");
  const transfers = source("app/transfers/page.tsx");
  const viewer = source("components/ReportViewer.tsx");

  assert.match(evidence, /Strong consensus/);
  assert.match(evidence, /Supported by/);
  assert.match(evidence, /View full source attribution/);
  assert.match(evidence, /Last updated:/);
  for (const page of [captaincy, transfers, viewer]) {
    assert.doesNotMatch(page, /% (?:expert )?confidence/);
    assert.doesNotMatch(page, /confidence-bar/);
  }
});

test("legacy public pipeline route redirects to protected admin", () => {
  const runner = source("app/pipeline-runner/page.tsx");

  assert.match(runner, /redirect\("\/admin"\)/);
  assert.doesNotMatch(runner, /runPipeline/);
});

test("API errors prefer backend detail messages", () => {
  const apiError = source("components/apiError.ts");

  assert.match(apiError, /error instanceof ApiError/);
  assert.match(apiError, /"detail" in detail/);
  assert.match(apiError, /return detail\.detail/);
  assert.match(apiError, /return `\$\{error\.status\} \$\{error\.statusText\}`/);
});

test("backend proxy forwards an HttpOnly admin session only to admin APIs", () => {
  const nextConfig = source("next.config.ts");
  const route = source("app/backend/[...path]/route.ts");

  assert.match(nextConfig, /output:\s*"standalone"/);
  assert.match(route, /process\.env\.API_PROXY_TARGET/);
  assert.match(route, /fpl_admin_session/);
  assert.match(route, /isAdminApi/);
  assert.match(route, /headers\.set\("authorization", `Bearer/);
  assert.doesNotMatch(source("src/lib/api.ts"), /PIPELINE_API_TOKEN/);
  assert.doesNotMatch(source("src/lib/api.ts"), /NEXT_PUBLIC_/);
});

test("polling stops on terminal states and has retry and timeout limits", () => {
  const api = source("src/lib/api.ts");

  assert.match(api, /current\.status === "pending" \|\| current\.status === "queued" \|\| current\.status === "running"/);
  assert.match(api, /maxConsecutiveErrors \?\? 3/);
  assert.match(api, /Date\.now\(\) >= deadline/);
  assert.match(api, /current = await getPipelineRun\(current\.run_id\)/);
});

test("public navigation and APIs do not expose operational controls", () => {
  const sidebar = source("components/Sidebar.tsx");
  const api = source("src/lib/api.ts");
  assert.doesNotMatch(sidebar, /\/admin|pipeline-runner|Pipeline Runner/);
  assert.match(api, /\/api\/recommendations\/latest/);
  assert.match(api, /\/api\/recommendations\/gameweeks/);
  assert.match(api, /getSelectedReport/);
  assert.match(api, /\/api\/admin\/pipeline\/run/);
});

test("admin dashboard exposes controls and internal failure details", () => {
  const admin = source("app/admin/(protected)/page.tsx");
  const guard = source("app/admin/(protected)/layout.tsx");
  assert.match(admin, /"Run pipeline"/);
  assert.match(admin, />Generate report</);
  assert.match(admin, />Failure details</);
  assert.match(admin, /disabled=\{isRunning\}/);
  assert.match(guard, /redirect\("\/admin\/login"\)/);
  assert.match(guard, /authorization: `Bearer/);
});
