from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Literal

from src.schemas.aggregate_report import ExpertTeamRevealItem
from src.services.normalization import (
    canonical_player_display,
    normalize_lookup_key,
    normalize_player_name,
)


TEAM_OF_WEEK_ALIASES = {
    "semeno": "antoine semenyo",
}

SquadSlot = Literal["starting_xi", "bench", "captain", "vice_captain"]


@dataclass(frozen=True)
class PlayerCandidate:
    name: str
    position: str | None = None
    price: float | None = None


@dataclass(frozen=True)
class RankedPlayer:
    name: str
    votes: int
    normalized_name: str
    position: str | None = None
    price: float | None = None


@dataclass(frozen=True)
class TeamConstraints:
    budget: float | None = None
    max_players: int = 11
    min_positions: dict[str, int] = field(default_factory=dict)
    max_positions: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SuggestedTeamSelection:
    starting_xi: list[RankedPlayer]
    bench: list[RankedPlayer]
    captain: RankedPlayer | None
    vice_captain: RankedPlayer | None
    player_votes: dict[str, int]
    bench_votes: dict[str, int]
    total_price: float | None = None
    position_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SuggestedTeamOfWeek:
    starting_xi: list[str]
    bench: list[str]
    captain: str | None
    vice_captain: str | None
    player_votes: dict[str, int]
    bench_votes: dict[str, int]
    total_price: float | None = None
    position_counts: dict[str, int] = field(default_factory=dict)


def rank_players(
    reveals: Iterable[ExpertTeamRevealItem],
    slot: SquadSlot = "starting_xi",
    player_pool: Iterable[PlayerCandidate] | None = None,
) -> list[RankedPlayer]:
    metadata = _build_player_metadata(player_pool)
    votes: Counter[str] = Counter()

    for reveal in reveals:
        values = _slot_values(reveal, slot)
        votes.update(player for item in values if (player := normalize_team_player(item)))

    return [
        _ranked_player(player, count, metadata)
        for player, count in _rank_counter(votes)
    ]


def apply_team_constraints(
    ranked_players: Iterable[RankedPlayer],
    constraints: TeamConstraints | None = None,
) -> list[RankedPlayer]:
    constraints = constraints or TeamConstraints()
    selected: list[RankedPlayer] = []
    selected_counts: Counter[str] = Counter()
    total_price = 0.0

    ranked = list(ranked_players)
    for player in ranked:
        if len(selected) >= constraints.max_players:
            break
        if not _can_add_player(player, selected_counts, total_price, constraints):
            continue
        selected.append(player)
        if player.position:
            selected_counts[_normalize_position(player.position)] += 1
        if player.price is not None:
            total_price += player.price

    if _position_minimums_met(selected_counts, constraints):
        return selected

    return _fill_position_minimums(selected, ranked, constraints)


def select_suggested_team_players(
    reveals: list[ExpertTeamRevealItem],
    player_pool: Iterable[PlayerCandidate] | None = None,
    constraints: TeamConstraints | None = None,
) -> SuggestedTeamSelection | None:
    if not reveals:
        return None

    constraints = constraints or TeamConstraints()
    ranked_starters = rank_players(reveals, "starting_xi", player_pool)
    if not ranked_starters:
        return None

    starting_xi = apply_team_constraints(ranked_starters, constraints)
    selected_names = {player.name for player in starting_xi}

    bench = [
        player
        for player in rank_players(reveals, "bench", player_pool)
        if player.name not in selected_names
    ][:4]
    captain = _first_ranked_player(reveals, "captain", player_pool)
    vice_captain = _first_ranked_player(reveals, "vice_captain", player_pool)

    total_price = _total_price(starting_xi)
    return SuggestedTeamSelection(
        starting_xi=starting_xi,
        bench=bench,
        captain=captain,
        vice_captain=vice_captain,
        player_votes={player.name: player.votes for player in ranked_starters},
        bench_votes={
            player.name: player.votes
            for player in rank_players(reveals, "bench", player_pool)
        },
        total_price=total_price,
        position_counts=_position_counts(starting_xi),
    )


def build_suggested_team_of_week(
    reveals: list[ExpertTeamRevealItem],
    player_pool: Iterable[PlayerCandidate] | None = None,
    constraints: TeamConstraints | None = None,
) -> SuggestedTeamOfWeek | None:
    selection = select_suggested_team_players(reveals, player_pool, constraints)
    if selection is None:
        return None

    return SuggestedTeamOfWeek(
        starting_xi=[player.name for player in selection.starting_xi],
        bench=[player.name for player in selection.bench],
        captain=selection.captain.name if selection.captain else None,
        vice_captain=selection.vice_captain.name if selection.vice_captain else None,
        player_votes=selection.player_votes,
        bench_votes=selection.bench_votes,
        total_price=selection.total_price,
        position_counts=selection.position_counts,
    )


def normalize_team_player(name: str | None) -> str:
    lookup = normalize_lookup_key(name)
    if lookup in TEAM_OF_WEEK_ALIASES:
        return TEAM_OF_WEEK_ALIASES[lookup]

    normalized = normalize_player_name(name or "")
    if normalized:
        return normalized
    return lookup


def _rank_counter(counter: Counter[str]) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))


def _slot_values(reveal: ExpertTeamRevealItem, slot: SquadSlot) -> list[str | None]:
    if slot == "starting_xi":
        return list(reveal.starting_xi)
    if slot == "bench":
        return list(reveal.bench)
    if slot == "captain":
        return [reveal.captain]
    return [reveal.vice_captain]


def _build_player_metadata(
    player_pool: Iterable[PlayerCandidate] | None,
) -> dict[str, PlayerCandidate]:
    metadata: dict[str, PlayerCandidate] = {}
    if player_pool is None:
        return metadata

    for player in player_pool:
        normalized = normalize_team_player(player.name)
        if normalized:
            metadata[normalized] = player
    return metadata


def _ranked_player(
    normalized_name: str,
    votes: int,
    metadata: dict[str, PlayerCandidate],
) -> RankedPlayer:
    candidate = metadata.get(normalized_name)
    return RankedPlayer(
        name=canonical_player_display(normalized_name),
        votes=votes,
        normalized_name=normalized_name,
        position=candidate.position if candidate else None,
        price=candidate.price if candidate else None,
    )


def _first_ranked_player(
    reveals: list[ExpertTeamRevealItem],
    slot: SquadSlot,
    player_pool: Iterable[PlayerCandidate] | None,
) -> RankedPlayer | None:
    ranked = rank_players(reveals, slot, player_pool)
    return ranked[0] if ranked else None


def _can_add_player(
    player: RankedPlayer,
    selected_counts: Counter[str],
    current_price: float,
    constraints: TeamConstraints,
) -> bool:
    if constraints.budget is not None and player.price is not None:
        if current_price + player.price > constraints.budget:
            return False

    if player.position is None:
        return True

    position = _normalize_position(player.position)
    max_position = _normalized_position_map(constraints.max_positions).get(position)
    return max_position is None or selected_counts[position] < max_position


def _position_minimums_met(
    selected_counts: Counter[str],
    constraints: TeamConstraints,
) -> bool:
    minimums = _normalized_position_map(constraints.min_positions)
    return all(selected_counts[position] >= minimum for position, minimum in minimums.items())


def _fill_position_minimums(
    selected: list[RankedPlayer],
    ranked: list[RankedPlayer],
    constraints: TeamConstraints,
) -> list[RankedPlayer]:
    selected_by_name = {player.normalized_name for player in selected}
    selected_counts = Counter(
        _normalize_position(player.position)
        for player in selected
        if player.position is not None
    )
    total_price = sum(player.price or 0 for player in selected)
    minimums = _normalized_position_map(constraints.min_positions)

    for position, minimum in minimums.items():
        while selected_counts[position] < minimum:
            replacement = next(
                (
                    player
                    for player in ranked
                    if player.normalized_name not in selected_by_name
                    and player.position is not None
                    and _normalize_position(player.position) == position
                    and _can_add_player(player, selected_counts, total_price, constraints)
                ),
                None,
            )
            if replacement is None:
                return selected

            selected.append(replacement)
            selected_by_name.add(replacement.normalized_name)
            selected_counts[position] += 1
            if replacement.price is not None:
                total_price += replacement.price

    return sorted(selected, key=lambda player: (-player.votes, player.normalized_name))[
        : constraints.max_players
    ]


def _normalized_position_map(values: dict[str, int]) -> dict[str, int]:
    return {_normalize_position(position): count for position, count in values.items()}


def _normalize_position(position: str) -> str:
    return normalize_lookup_key(position).upper()


def _total_price(players: list[RankedPlayer]) -> float | None:
    prices = [player.price for player in players if player.price is not None]
    if not prices:
        return None
    return round(sum(prices), 2)


def _position_counts(players: list[RankedPlayer]) -> dict[str, int]:
    counts = Counter(
        _normalize_position(player.position)
        for player in players
        if player.position is not None
    )
    return dict(sorted(counts.items()))


__all__ = [
    "PlayerCandidate",
    "RankedPlayer",
    "SuggestedTeamOfWeek",
    "SuggestedTeamSelection",
    "TeamConstraints",
    "apply_team_constraints",
    "build_suggested_team_of_week",
    "normalize_team_player",
    "rank_players",
    "select_suggested_team_players",
]
