import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import test from "node:test";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));

function source(path) {
  return readFileSync(join(root, path), "utf8");
}

async function loadTypeScript(relativePath) {
  const path = join(root, relativePath);
  const compiled = ts.transpileModule(readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}

const season = await loadTypeScript("lib/admin/season.ts");
const api = await loadTypeScript("src/lib/api.ts");

test("admin form includes a required season field", () => {
  const admin = source("app/admin/(protected)/page.tsx");

  assert.match(admin, /<span>Season<\/span>/);
  assert.match(admin, /pattern="\[0-9\]\{4\}-\[0-9\]\{2\}"/);
  assert.match(admin, /placeholder="2025-26"/);
  assert.match(admin, /required\s+type="text"/);
});

test("season validation rejects missing, malformed, and non-consecutive seasons", () => {
  assert.equal(season.seasonValidationError(""), "Season is required.");
  assert.match(season.seasonValidationError("25-26"), /YYYY-YY/);
  assert.match(season.seasonValidationError("2025/26"), /YYYY-YY/);
  assert.match(season.seasonValidationError("2025-27"), /consecutive years/);
  assert.equal(season.seasonValidationError("2025-26"), null);
  assert.equal(season.seasonValidationError("2099-00"), null);
});

test("valid season and gameweek values build one canonical admin input", () => {
  assert.deepEqual(season.buildAdminPipelineInput(" 2025-26 ", "35", "1"), {
    season: "2025-26",
    gameweek: 35,
    per_expert_limit: 1
  });
});

test("run pipeline and generate report requests both include season", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ run_id: "run-1", status: "queued" }), {
      headers: { "content-type": "application/json" },
      status: 200
    });
  };

  const input = { season: "2025-26", gameweek: 35, per_expert_limit: 1 };
  try {
    await api.runPipeline(input);
    await api.generateReport(input);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(calls.map(({ url }) => url), [
    "/backend/api/admin/pipeline/run",
    "/backend/api/admin/reports/generate"
  ]);
  for (const { options } of calls) {
    assert.equal(options.method, "POST");
    assert.deepEqual(JSON.parse(options.body), { input_data: input });
  }
});

test("invalid seasons return before either admin API action", () => {
  const admin = source("app/admin/(protected)/page.tsx");
  const validation = admin.indexOf("const validationError = seasonValidationError(season)");
  const earlyReturn = admin.indexOf("if (validationError) return");
  const pipelineCall = admin.indexOf("await runPipeline(input)");
  const reportCall = admin.indexOf("await generateReport(input)");

  assert.ok(validation >= 0);
  assert.ok(earlyReturn > validation);
  assert.ok(pipelineCall > earlyReturn);
  assert.ok(reportCall > earlyReturn);
});
