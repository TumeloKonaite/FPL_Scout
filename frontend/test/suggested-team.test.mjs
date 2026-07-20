import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";

const path = fileURLToPath(new URL("../components/suggestedTeam.ts", import.meta.url));
const source = readFileSync(path, "utf8").replace(/^import type .*?;\n/m, "");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText;
const utils = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

const counts = { "3-4-3": [3, 4, 3], "3-5-2": [3, 5, 2], "4-4-2": [4, 4, 2], "5-3-2": [5, 3, 2] };
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

test("rejects unsupported positions, duplicate IDs, missing names, and invalid numbers", () => {
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

test("groups normalized positions and maps them to pitch rows", () => {
  const grouped = utils.groupPlayersByPosition(lineup("3-5-2"));
  assert.deepEqual([grouped.goalkeeper.length, grouped.defenders.length, grouped.midfielders.length, grouped.forwards.length], [1, 3, 5, 2]);
  const team = utils.mapPlayersToLineup(grouped);
  assert.equal(team.squad.gk.name, "GK 1");
  assert.equal(team.squad.cm.length, 5);
  const rendered = [team.squad.gk, ...team.squad.df, ...team.squad.cm, ...team.squad.fw];
  assert.equal(rendered.length, 11);
  assert.deepEqual(rendered.map(({ name, number }) => ({ name, number })), lineup("3-5-2").map(({ name, number }) => ({ name, number })));
});

test("component declares all safe states before invoking the pitch", () => {
  const component = readFileSync(fileURLToPath(new URL("../components/SuggestedTeamPitch.tsx", import.meta.url)), "utf8");
  for (const copy of ["Loading suggested formation", "Generate a suggested team", "could not be loaded", "incomplete or invalid", "Suggested Starting XI"]) assert.match(component, new RegExp(copy));
  assert.ok(component.indexOf("if (!validation.valid)") < component.indexOf("<SoccerLineUp"));
  const page = readFileSync(fileURLToPath(new URL("../app/suggested-team/page.tsx", import.meta.url)), "utf8");
  assert.match(page, /SuggestedTeamTable players=\{detailedPlayers\}/);
  assert.match(page, /players=\{suggestedTeam\?\.startingXi\}/);
});
