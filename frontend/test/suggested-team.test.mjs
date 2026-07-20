import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";

const path = fileURLToPath(new URL("../components/suggestedTeam.ts", import.meta.url));
const source = readFileSync(path, "utf8").replace(/^import type .*?;\n/m, "");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
const utils = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

const counts = {
  "3-4-3": [3, 4, 3], "3-5-2": [3, 5, 2], "4-3-3": [4, 3, 3], "4-4-2": [4, 4, 2],
  "4-5-1": [4, 5, 1], "5-2-3": [5, 2, 3], "5-3-2": [5, 3, 2], "5-4-1": [5, 4, 1]
};
function lineup(formation) {
  const [defs, mids, fwds] = counts[formation];
  let id = 1;
  const make = (amount, position) => Array.from({ length: amount }, () => ({ playerId: id, name: `${position} ${id}`, number: id++, position }));
  return [...make(1, "GK"), ...make(defs, "DEF"), ...make(mids, "MID"), ...make(fwds, "FWD")];
}

for (const formation of Object.keys(counts)) test(`validates ${formation}`, () => assert.equal(utils.validateStartingXi(lineup(formation), formation).valid, true));

test("rejects too few and too many players", () => {
  assert.equal(utils.validateStartingXi(lineup("3-4-3").slice(0, 10)).valid, false);
  assert.equal(utils.validateStartingXi([...lineup("3-4-3"), { playerId: 12, name: "Extra", number: 12, position: "MID" }]).valid, false);
});

test("rejects missing and multiple goalkeepers", () => {
  const noGoalkeeper = lineup("3-4-3").map((player) => player.position === "GK" ? { ...player, position: "DEF" } : player);
  const twoGoalkeepers = lineup("3-4-3").map((player, index) => index === 1 ? { ...player, position: "GK" } : player);
  assert.equal(utils.validateStartingXi(noGoalkeeper).valid, false);
  assert.equal(utils.validateStartingXi(twoGoalkeepers).valid, false);
});

test("rejects unsupported positions, duplicate IDs, missing names, and invalid supplied numbers", () => {
  const mutate = (key, value) => lineup("3-4-3").map((player, index) => index === 1 ? { ...player, [key]: value } : player);
  assert.equal(utils.validateStartingXi(mutate("position", "WING")).valid, false);
  assert.equal(utils.validateStartingXi(mutate("playerId", 1)).valid, false);
  assert.equal(utils.validateStartingXi(mutate("name", " ")).valid, false);
  assert.equal(utils.validateStartingXi(mutate("number", 0)).valid, false);
});

test("rejects mismatched and unsupported formations", () => {
  assert.equal(utils.validateStartingXi(lineup("3-4-3"), "4-4-2").valid, false);
  const unsupported = lineup("4-4-2").map((player, index) => index === 1 || index === 2 ? { ...player, position: "FWD" } : player);
  assert.equal(utils.validateStartingXi(unsupported).valid, false);
});

test("groups normalized positions and derives the pitch rows", () => {
  const grouped = utils.groupPlayersByPosition(lineup("3-5-2"));
  assert.deepEqual([grouped.goalkeeper.length, grouped.defenders.length, grouped.midfielders.length, grouped.forwards.length], [1, 3, 5, 2]);
  assert.equal(utils.deriveFormation(lineup("3-5-2")), "3-5-2");
});

test("page declares loading, unavailable, warning, pitch, bench, and table states", () => {
  const component = readFileSync(fileURLToPath(new URL("../components/SuggestedTeamPitch.tsx", import.meta.url)), "utf8");
  for (const copy of ["Suggested XI", "Captain:", "Vice-captain:", "football-pitch"]) assert.match(component, new RegExp(copy));
  const page = readFileSync(fileURLToPath(new URL("../app/suggested-team/page.tsx", import.meta.url)), "utf8");
  assert.match(page, /SuggestedTeamTable players=\{team\.allPlayers\}/);
  assert.match(page, /<SuggestedTeamPitch team=\{team\}/);
  assert.match(page, /<SuggestedTeamBench team=\{team\}/);
  assert.match(page, /Suggested team not available yet/);
  assert.match(page, /Suggested team data is incomplete/);
  assert.match(page, /SuggestedTeamSkeleton/);
});

test("normalizes one shared lineup, ordered bench, captaincy, and partial metadata", () => {
  const starters = lineup("4-4-2").map((player) => player.playerId === 6 ? { ...player, number: undefined } : player);
  const bench = [
    { playerId: 14, name: "Bench MID", position: "MID", benchOrder: 3 },
    { playerId: 12, name: "Bench GK", position: "GK", benchOrder: 1 },
    { playerId: 13, name: "Bench DEF", position: "DEF", benchOrder: 2 },
    { playerId: 15, name: "Bench FWD", position: "FWD", benchOrder: 4 }
  ];
  const team = utils.normalizeSuggestedTeam({ starters, bench, captainPlayerId: 6, viceCaptainPlayerId: 10 });
  assert.equal(team.formation, "4-4-2");
  assert.equal(team.allPlayers.length, 15);
  assert.deepEqual(team.bench.map((player) => player.playerId), [12, 13, 14, 15]);
  assert.equal(team.captain.playerId, 6);
  assert.equal(team.viceCaptain.playerId, 10);
  assert.equal(team.warnings.length, 0);
});
