import { describeLineup, playerLabel, type NormalizedSuggestedTeam, type SuggestedPlayer } from "./suggestedTeam";

export type SuggestedTeamPitchProps = {
  team: NormalizedSuggestedTeam;
  gameweek?: number | null;
};

function PlayerMarker({ player, captain, viceCaptain }: { player: SuggestedPlayer; captain: SuggestedPlayer | null; viceCaptain: SuggestedPlayer | null }) {
  const label = playerLabel(player, captain?.playerId, viceCaptain?.playerId);
  const role = player.playerId === captain?.playerId || player.captain ? "captain" : player.playerId === viceCaptain?.playerId || player.viceCaptain ? "vice-captain" : null;
  const shirtNumber = player.shirtNumber ?? player.number;
  return (
    <div className={`pitch-player${role ? ` ${role}` : ""}`} title={`${label} · ${player.position}`}>
      <span className="player-shirt" aria-hidden="true">{shirtNumber ?? ""}</span>
      <span className="pitch-player-name">{label}</span>
    </div>
  );
}

export function SuggestedTeamPitch({ team, gameweek }: SuggestedTeamPitchProps) {
  const description = describeLineup(team.formation, team.groupedPlayers);
  const rows = [
    ["Forwards", team.groupedPlayers.forwards],
    ["Midfielders", team.groupedPlayers.midfielders],
    ["Defenders", team.groupedPlayers.defenders],
    ["Goalkeeper", team.groupedPlayers.goalkeeper]
  ] as const;

  return (
    <section className="pitch-card" aria-labelledby="suggested-formation-title" aria-describedby="suggested-lineup-description">
      <div className="pitch-heading">
        <div>
          <span className="eyebrow">{gameweek ? `Gameweek ${gameweek}` : "Current gameweek"}</span>
          <h2 id="suggested-formation-title">Suggested XI · {team.formation ?? "Formation unavailable"}</h2>
          <p className="captaincy-summary">Captain: {team.captain?.name ?? "Not available"} · Vice-captain: {team.viceCaptain?.name ?? "Not available"}</p>
        </div>
        {team.formation ? <span className="formation-badge">{team.formation}</span> : null}
      </div>
      <p className="visually-hidden" id="suggested-lineup-description">{description}</p>
      <div className="pitch-frame" title={description}>
        <div className="football-pitch">
          <span className="pitch-centre-circle" aria-hidden="true" />
          {rows.map(([label, players]) => (
            <div className={`pitch-row pitch-row-${label.toLowerCase()}`} aria-label={label} key={label}>
              {players.map((player) => <PlayerMarker key={player.playerId} player={player} captain={team.captain} viceCaptain={team.viceCaptain} />)}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
