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

test("page declares loading, unavailable, warning, pitch, bench, and provenance states", () => {
  const component = readFileSync(fileURLToPath(new URL("../components/SuggestedTeamPitch.tsx", import.meta.url)), "utf8");
  for (const copy of ["teamTitle", "Captain:", "Vice-captain:", "football-pitch", "playerSupportLabel"]) assert.match(component, new RegExp(copy));
  const page = readFileSync(fileURLToPath(new URL("../app/suggested-team/page.tsx", import.meta.url)), "utf8");
  assert.match(page, /<SuggestedTeamPitch team=\{team\}/);
  assert.match(page, /<SuggestedTeamBench team=\{team\}/);
  assert.match(page, /<SuggestedTeamConsensusPanel team=\{team\}/);
  assert.match(page, /Suggested team unavailable/);
  assert.match(page, /kasifpl-team-layout/);
  assert.match(page, /useSelectedReport/);
  assert.match(page, /ReportLoadingState/);
});

test("refined team UI exposes support, captaincy, bench roles, and provenance", () => {
  const player = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/PlayerTile.tsx", import.meta.url)), "utf8");
  const bench = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/SuggestedTeamBench.tsx", import.meta.url)), "utf8");
  const consensus = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/SuggestedTeamConsensusPanel.tsx", import.meta.url)), "utf8");
  const styles = readFileSync(fileURLToPath(new URL("../components/kasifpl/styles/kasifpl.css", import.meta.url)), "utf8");

  assert.match(player, /player\.shirtNumber != null/);
  assert.doesNotMatch(player, /player\.number/);
  assert.match(player, /loading="lazy"/);
  assert.match(player, /alt=\{`\$\{player\.name\} headshot`\}/);
  assert.match(player, /onError=\{\(\) => setFailedImageUrl/);
  assert.match(player, /onError=\{\(\) => setFailedBadgeUrl/);
  assert.match(player, /kasifpl-player__fallback-position/);
  assert.match(player, /player\.teamBadgeUrl/);
  assert.match(player, /starterSupportCount/);
  assert.match(player, /squadSupportCount/);
  assert.match(player, /captainSupportCount/);
  assert.match(player, /viceCaptainSupportCount/);
  assert.match(player, /contributingExpertIds/);
  assert.match(player, /contributingRevealIds/);
  assert.match(bench, /Substitute goalkeeper/);
  assert.match(bench, /First/);
  assert.match(consensus, /Median XI support/);
  assert.match(consensus, /Split consensus/);
  assert.match(consensus, /contributingExperts/);
  assert.match(consensus, /excludedRevealCount/);
  assert.match(consensus, /authoritativeCataloguePositions/);
  assert.match(styles, /grid-template-columns: minmax\(0, 7fr\) minmax\(300px, 3fr\)/);
  assert.match(styles, /max-height: 700px/);
  assert.match(styles, /kasifpl-player--support-limited/);
  assert.match(styles, /kasifpl-player__headshot/);
  assert.match(styles, /object-fit: contain/);
});

test("suggested-player media fields remain optional", () => {
  const types = readFileSync(fileURLToPath(new URL("../components/kasifpl/types.ts", import.meta.url)), "utf8");
  for (const field of ["playerCode", "teamCode", "imageUrl", "teamBadgeUrl"]) {
    assert.match(types, new RegExp(`${field}\\?:`));
  }
});

test("player tiles render optional headshots and club badges", () => {
  const player = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/PlayerTile.tsx", import.meta.url)), "utf8");
  assert.match(player, /showHeadshot \? \(/);
  assert.match(player, /src=\{player\.imageUrl \?\? undefined\}/);
  assert.match(player, /src=\{player\.teamBadgeUrl \?\? undefined\}/);
});

test("player tiles retain a position fallback when media is missing", () => {
  const player = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/PlayerTile.tsx", import.meta.url)), "utf8");
  assert.match(player, /const showHeadshot = Boolean\(player\.imageUrl\)/);
  assert.match(player, /kasifpl-player__media--fallback/);
  assert.match(player, /\{player\.position\}/);
});

test("player tiles remove failed images without removing player details", () => {
  const player = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/PlayerTile.tsx", import.meta.url)), "utf8");
  assert.match(player, /failedImageUrl !== player\.imageUrl/);
  assert.match(player, /failedBadgeUrl !== player\.teamBadgeUrl/);
  for (const detail of ["kasifpl-player__name", "kasifpl-player__support", "kasifpl-player__price", "kasifpl-player__badge"]) {
    assert.match(player, new RegExp(detail));
  }
});

test("exported pitch rejects incomplete and mismatched lineups", () => {
  const shared = readFileSync(fileURLToPath(new URL("../components/kasifpl/components/_shared.tsx", import.meta.url)), "utf8");
  assert.match(shared, /starters\.length !== 11/);
  assert.match(shared, /new Set\(starters\.map/);
  assert.match(shared, /gk\.length !== 1/);
  assert.match(shared, /team\.formation\.trim\(\) !== derivedFormation/);
});

test("does not normalize an insufficient-evidence payload as a lineup", () => {
  assert.equal(utils.normalizeSuggestedTeam({
    constructionStatus: "insufficient_evidence",
    failureReason: "fewer_than_two_eligible_experts",
    startingXi: lineup("3-4-3")
  }), null);
});

test("does not normalize a consensus status without a valid full squad", () => {
  assert.equal(utils.normalizeSuggestedTeam({
    constructionStatus: "consensus",
    constructionMethod: "vote_based_consensus",
    startingXi: lineup("3-4-3"),
    bench: [],
    captainPlayerId: 1,
    viceCaptainPlayerId: 2
  }), null);
});

test("uses construction provenance for safe labels and agreement copy", () => {
  assert.equal(utils.teamTitle("vote_based_consensus"), "Consensus XI");
  assert.equal(utils.teamTitle("single_reveal"), "Expert XI");
  assert.equal(utils.teamTitle("legacy_snapshot"), "Suggested XI");
  assert.equal(utils.teamTitle("insufficient_evidence"), null);
  assert.equal(utils.agreementLabel("strong"), "Strong agreement");
  assert.equal(utils.agreementLabel("split"), "Split opinion");
});

test("uses starter support for starters, squad support for bench, and unknown for legacy", () => {
  const support = {
    eligibleExpertCount: 6,
    starterSupportCount: 4,
    starterSupportPercentage: 66.7,
    squadSupportCount: 5,
    squadSupportPercentage: 83.3,
    captainSupportCount: 2,
    captainSupportPercentage: 33.3,
    viceCaptainSupportCount: 1,
    viceCaptainSupportPercentage: 16.7,
    contributingExpertIds: ["a", "b"]
  };
  assert.equal(utils.playerSupportLabel({ playerId: 1, name: "A", position: "GK", isStarter: true, support }), "Started by 4 of 6 experts");
  assert.equal(utils.playerSupportLabel({ playerId: 2, name: "B", position: "DEF", isStarter: false, support }), "Selected by 5 of 6 experts");
  assert.equal(utils.playerSupportLabel({ playerId: 3, name: "Legacy", position: "MID" }), "Expert support unavailable");
});

test("treats an old consensus flag without provenance as a legacy snapshot", () => {
  const legacy = utils.normalizeSuggestedTeam({
    constructionStatus: "consensus",
    startingXi: lineup("3-4-3")
  });
  assert.equal(legacy.constructionMethod, "legacy_snapshot");
  assert.equal(legacy.consensusStrength, "insufficient");
  assert.equal(legacy.provenanceAvailable, false);
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
