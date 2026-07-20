"use client";

import dynamic from "next/dynamic";
import { describeLineup, mapPlayersToLineup, validateStartingXi, type SuggestedPlayer } from "./suggestedTeam";

const SoccerLineUp = dynamic(() => import("react-soccer-lineup"), {
  loading: () => <div className="pitch-library-loading" aria-hidden="true" />,
  ssr: false
});

export type SuggestedTeamPitchProps = {
  formation?: string;
  players?: SuggestedPlayer[];
  isLoading?: boolean;
  error?: string | null;
};

const INVALID_MESSAGE = "The suggested formation could not be displayed because the starting lineup is incomplete or invalid.";

export function SuggestedTeamPitch({ formation, players, isLoading = false, error = null }: SuggestedTeamPitchProps) {
  if (isLoading) return <div className="pitch-state pitch-state-loading" role="status">Loading suggested formation…</div>;
  if (error) return <div className="pitch-state pitch-state-error" role="alert">The suggested team could not be loaded. Please try again.</div>;
  if (!players?.length) return <div className="pitch-state">Generate a suggested team to view its formation.</div>;

  const validation = validateStartingXi(players, formation);
  if (!validation.valid) {
    console.warn("SuggestedTeamPitch rejected an invalid lineup", { reason: validation.reason, formation });
    return <div className="pitch-state pitch-state-error" role="status">{INVALID_MESSAGE}</div>;
  }

  const description = describeLineup(validation.formation, validation.groupedPlayers);
  return (
    <section className="pitch-card" aria-labelledby="suggested-formation-title" aria-describedby="suggested-lineup-description">
      <div className="pitch-heading">
        <div><span className="eyebrow">Recommended lineup</span><h2 id="suggested-formation-title">Suggested Starting XI — {validation.formation}</h2></div>
        <span className="formation-badge">{validation.formation}</span>
      </div>
      <p className="visually-hidden" id="suggested-lineup-description">{description}</p>
      <div className="pitch-frame" title={description}>
        <SoccerLineUp size="responsive" orientation="vertical" color="#17885f" pattern="lines" homeTeam={mapPlayersToLineup(validation.groupedPlayers)} />
      </div>
    </section>
  );
}
