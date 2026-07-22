import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";

async function loadUtility(relativePath) {
  const path = fileURLToPath(new URL(relativePath, import.meta.url));
  const compiled = ts.transpileModule(readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}

const selection = await loadUtility("../lib/reports/reportSelection.ts");
const href = await loadUtility("../lib/reports/reportHref.ts");
const status = await loadUtility("../lib/reports/reportStatus.ts");

const seasons = [{
  season: "2026-27",
  gameweeks: [
    { gameweek: 12, last_updated_at: "2026-10-30T15:00:00Z", has_suggested_team: true },
    { gameweek: 11, last_updated_at: "2026-10-23T15:00:00Z", has_suggested_team: false }
  ]
}, {
  season: "2025-26",
  gameweeks: [{ gameweek: 38, last_updated_at: "2026-05-20T15:00:00Z", has_suggested_team: true }]
}];

test("parses complete URL selections and rejects malformed values", () => {
  assert.deepEqual(selection.parseReportSelection(new URLSearchParams("season=2026-27&gameweek=12")), { season: "2026-27", gameweek: 12 });
  assert.equal(selection.parseReportSelection(new URLSearchParams()), null);
  assert.equal(Number.isNaN(selection.parseReportSelection(new URLSearchParams("season=2026-27&gameweek=nope")).gameweek), true);
});

test("validates availability and resolves the newest report by timestamp", () => {
  assert.equal(selection.selectionExists(seasons, { season: "2026-27", gameweek: 12 }), true);
  assert.equal(selection.selectionExists(seasons, { season: "2026-27", gameweek: 10 }), false);
  assert.deepEqual(selection.newestSelection(seasons), { season: "2026-27", gameweek: 12 });
});

test("report links retain selection, existing params, and fragments", () => {
  assert.equal(href.reportHref("/reports?view=full#risks", { season: "2026-27", gameweek: 12 }), "/reports?view=full&season=2026-27&gameweek=12#risks");
  assert.equal(href.reportHref("/reports", null), "/reports");
});

test("historical and passed deadlines never produce an upcoming state", () => {
  assert.equal(status.deadlineState("2099-01-01T00:00:00Z", true, 0), "passed");
  assert.equal(status.deadlineState("2020-01-01T00:00:00Z", false, Date.now()), "passed");
  assert.equal(status.deadlineState(null, false), "missing");
  assert.equal(status.deadlineState("2099-01-01T00:00:00Z", false, 0), "upcoming");
});
