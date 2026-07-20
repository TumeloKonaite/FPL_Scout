import { playerLabel, type NormalizedSuggestedTeam } from "./suggestedTeam";

export function SuggestedTeamBench({ team }: { team: NormalizedSuggestedTeam }) {
  if (!team.bench.length) return null;
  return (
    <section className="bench-card" aria-labelledby="suggested-team-bench-title">
      <div className="bench-heading"><span className="eyebrow">Substitutes</span><h2 id="suggested-team-bench-title">Bench</h2></div>
      <ol className="bench-list">
        {team.bench.map((player) => (
          <li key={player.playerId}>
            <span className="bench-order">{player.benchOrder}</span>
            <span><strong>{playerLabel(player, team.captain?.playerId, team.viceCaptain?.playerId)}</strong><small>{player.position}{player.position === "GK" ? " · Substitute goalkeeper" : ""}</small></span>
          </li>
        ))}
      </ol>
    </section>
  );
}
