import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import test from "node:test";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = (path) => readFileSync(join(root, path), "utf8");

test("an empty report index is classified as a missing report", () => {
  const provider = source("components/useSelectedReport.tsx");

  assert.match(provider, /availableSeasons\.length === 0/);
  assert.match(provider, /const isMissingReport = hasNoPublishedReports \|\|/);
});

test("public report pages render a clear zero-report state", () => {
  const states = source("components/report-selection/ReportStates.tsx");
  assert.match(states, /No published reports are available yet\./);

  for (const page of [
    "app/dashboard/page.tsx",
    "app/reports/page.tsx",
    "app/captaincy/page.tsx",
    "app/transfers/page.tsx",
    "app/expert-consensus/page.tsx",
    "app/suggested-team/page.tsx"
  ]) {
    assert.match(source(page), /isMissingReport \? <MissingReportState \/>/, page);
  }
});

test("selectors remain disabled when the index has no seasons", () => {
  const selector = source("components/report-selection/GameweekSelector.tsx");
  assert.match(selector, /const disabled = isLoadingIndex \|\| !availableSeasons\.length/);
  assert.match(selector, /isLoadingIndex \? "Loading…" : "Unavailable"/);
});
