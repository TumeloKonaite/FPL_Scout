from __future__ import annotations

import re
import zlib
from collections import Counter

from src.app.domain.reports.team_of_week import normalize_team_player
from src.schemas.aggregate_report import ExpertTeamRevealItem
from src.schemas.final_report import SuggestedPlayer, SuggestedTeam


SUPPORTED_FORMATIONS = {
    "3-4-3",
    "3-5-2",
    "4-3-3",
    "4-4-2",
    "4-5-1",
    "5-2-3",
    "5-3-2",
    "5-4-1",
}
POSITION_SUFFIX = re.compile(r"\s+(GK|DEF|MID|FWD)\s*$", re.IGNORECASE)


def build_suggested_team_from_reveals(
    reveals: list[ExpertTeamRevealItem],
    position_catalog: dict[str, str] | None = None,
) -> SuggestedTeam | None:
    """Use the best complete XI whose positions are explicit in the source data.

    Some analysis outputs annotate every current-team player with an FPL position while
    keeping clean names in ``starting_xi``. This adapter joins those two lists. It never
    infers a position from player order or football knowledge.
    """
    candidates = sorted(
        reveals,
        key=lambda reveal: (-(reveal.confidence or 0), reveal.expert_name.casefold()),
    )
    for reveal in candidates:
        team = _team_from_reveal(reveal, position_catalog or {})
        if team is not None:
            return team
    return None


def build_explicit_position_catalog(
    reveals: list[ExpertTeamRevealItem],
) -> dict[str, str]:
    catalog: dict[str, str] = {}
    conflicts: set[str] = set()
    for reveal in reveals:
        for raw_name, raw_position in reveal.player_positions.items():
            name = normalize_team_player(raw_name)
            position = raw_position.upper()
            if not name:
                continue
            if name in catalog and catalog[name] != position:
                conflicts.add(name)
            else:
                catalog[name] = position
        for raw_name in reveal.current_team:
            match = POSITION_SUFFIX.search(raw_name)
            if match is None:
                continue
            name = normalize_team_player(raw_name[: match.start()].strip())
            position = match.group(1).upper()
            if not name:
                continue
            if name in catalog and catalog[name] != position:
                conflicts.add(name)
            else:
                catalog[name] = position
    for name in conflicts:
        catalog.pop(name, None)
    return catalog


def _team_from_reveal(
    reveal: ExpertTeamRevealItem,
    position_catalog: dict[str, str],
) -> SuggestedTeam | None:
    if len(reveal.starting_xi) != 11:
        return None

    metadata = dict(position_catalog)
    metadata.update(build_explicit_position_catalog([reveal]))

    players: list[SuggestedPlayer] = []
    used_ids: set[int] = set()
    for squad_number, starting_name in enumerate(reveal.starting_xi, start=1):
        normalized_name = normalize_team_player(starting_name)
        position = metadata.get(normalized_name)
        if position is None:
            return None
        display_name = starting_name.strip()
        player_id = zlib.crc32(normalized_name.encode("utf-8"))
        if player_id <= 0 or player_id in used_ids:
            return None
        used_ids.add(player_id)
        players.append(
            SuggestedPlayer(
                playerId=player_id,
                name=display_name,
                number=squad_number,
                position=position,
                captain=(normalized_name == normalize_team_player(reveal.captain)),
                viceCaptain=(
                    normalized_name == normalize_team_player(reveal.vice_captain)
                ),
            )
        )

    counts = Counter(player.position for player in players)
    if counts["GK"] != 1:
        return None
    formation = f'{counts["DEF"]}-{counts["MID"]}-{counts["FWD"]}'
    if formation not in SUPPORTED_FORMATIONS:
        return None
    bench: list[SuggestedPlayer] = []
    for bench_order, bench_name in enumerate(reveal.bench[:4], start=1):
        normalized_name = normalize_team_player(bench_name)
        position = metadata.get(normalized_name)
        if position is None:
            continue
        player_id = zlib.crc32(normalized_name.encode("utf-8"))
        if player_id <= 0 or player_id in used_ids:
            continue
        used_ids.add(player_id)
        bench.append(
            SuggestedPlayer(
                playerId=player_id,
                name=bench_name.strip(),
                position=position,
                captain=(normalized_name == normalize_team_player(reveal.captain)),
                viceCaptain=(normalized_name == normalize_team_player(reveal.vice_captain)),
                isStarter=False,
                benchOrder=bench_order,
            )
        )

    all_players = [*players, *bench]
    captain = next((player for player in all_players if player.captain), None)
    vice_captain = next((player for player in all_players if player.viceCaptain), None)
    return SuggestedTeam(
        formation=formation,
        startingXi=players,
        bench=bench,
        players=all_players,
        captainPlayerId=captain.playerId if captain else None,
        viceCaptainPlayerId=vice_captain.playerId if vice_captain else None,
    )


__all__ = [
    "build_explicit_position_catalog",
    "build_suggested_team_from_reveals",
]
