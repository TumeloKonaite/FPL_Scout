import type { SuggestedPlayer } from "./suggestedTeam";

const value = (item: string | number | null | undefined, suffix = "") => item === undefined || item === null ? "—" : `${item}${suffix}`;

export function SuggestedTeamTable({ players }: { players: SuggestedPlayer[] }) {
  if (!players.length) return null;
  return (
    <section className="data-card suggested-team-table-card" aria-labelledby="suggested-team-details-title">
      <div className="table-heading"><div><span className="eyebrow">Player detail</span><h2 id="suggested-team-details-title">Suggested team details</h2></div><span>{players.length} players</span></div>
      <div className="table-scroll"><table className="suggested-team-table">
        <thead><tr><th>Player</th><th>Pos</th><th>Club</th><th>Price</th><th>Pred. pts</th><th>Own.</th><th>Minutes</th><th>FDR</th><th>Status</th></tr></thead>
        <tbody>{players.map((player, index) => <tr key={`${player.playerId}-${index}`}>
          <th scope="row"><span className="player-number">{player.number}</span>{player.name}</th>
          <td>{player.position}</td><td>{value(player.club)}</td><td>{value(player.price === null || player.price === undefined ? null : `£${player.price.toFixed(1)}m`)}</td>
          <td>{value(player.predictedPoints)}</td><td>{value(player.ownership, "%")}</td><td>{value(player.expectedMinutes)}</td><td>{value(player.fixtureDifficulty)}</td>
          <td>{player.captain ? "Captain" : player.viceCaptain ? "Vice captain" : player.isStarter === false ? "Bench" : "Starter"}</td>
        </tr>)}</tbody>
      </table></div>
    </section>
  );
}
