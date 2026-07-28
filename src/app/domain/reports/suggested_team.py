from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Literal

from src.app.domain.reports.team_of_week import normalize_team_player
from src.schemas.aggregate_report import ExpertTeamRevealItem
from src.schemas.final_report import (
    ContributingReveal,
    SuggestedPlayer,
    SuggestedTeam,
)


Position = Literal["GK", "DEF", "MID", "FWD"]
CaptaincyFallback = Literal["require_evidence", "starter_support"]

# This order is the final tie-break when aggregate formation scores are equal.
FORMATION_ORDER: tuple[tuple[str, Mapping[Position, int]], ...] = (
    ("3-4-3", {"GK": 1, "DEF": 3, "MID": 4, "FWD": 3}),
    ("3-5-2", {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2}),
    ("4-3-3", {"GK": 1, "DEF": 4, "MID": 3, "FWD": 3}),
    ("4-4-2", {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}),
    ("4-5-1", {"GK": 1, "DEF": 4, "MID": 5, "FWD": 1}),
    ("5-2-3", {"GK": 1, "DEF": 5, "MID": 2, "FWD": 3}),
    ("5-3-2", {"GK": 1, "DEF": 5, "MID": 3, "FWD": 2}),
    ("5-4-1", {"GK": 1, "DEF": 5, "MID": 4, "FWD": 1}),
)
SQUAD_QUOTAS: Mapping[Position, int] = {
    "GK": 2,
    "DEF": 5,
    "MID": 5,
    "FWD": 3,
}

FAILURE_MISSING_CATALOGUE = "authoritative_player_catalogue_unavailable"
FAILURE_TOO_FEW_EXPERTS = "fewer_than_two_eligible_experts"
FAILURE_INSUFFICIENT_PLAYERS = "insufficient_resolved_players"
FAILURE_NO_FORMATION = "no_valid_starting_formation"
FAILURE_NO_SQUAD = "no_valid_full_squad"
FAILURE_NO_CAPTAINCY = "insufficient_captaincy_evidence"
POSITION_SUFFIX = re.compile(r"\s+(GK|DEF|MID|FWD)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CataloguePlayer:
    official_player_id: int
    canonical_name: str
    position: Position
    club: str | None = None
    price: float | None = None
    aliases: tuple[str, ...] = ()


class PlayerCatalogue:
    """Authoritative player lookup with ambiguity-safe name resolution."""

    def __init__(self, players: Iterable[CataloguePlayer]) -> None:
        self._players: dict[int, CataloguePlayer] = {}
        candidates: dict[str, set[int]] = {}
        for player in players:
            if player.official_player_id <= 0 or player.position not in SQUAD_QUOTAS:
                continue
            self._players[player.official_player_id] = player
            for name in (player.canonical_name, *player.aliases):
                key = normalize_team_player(name)
                if key:
                    candidates.setdefault(key, set()).add(player.official_player_id)
        self._lookup = {
            key: next(iter(ids)) for key, ids in candidates.items() if len(ids) == 1
        }

    def resolve(self, name: str | None) -> CataloguePlayer | None:
        player_id = self._lookup.get(normalize_team_player(name))
        return self._players.get(player_id) if player_id is not None else None

    def by_id(self, player_id: int) -> CataloguePlayer | None:
        return self._players.get(player_id)

    def __bool__(self) -> bool:
        return bool(self._players)


@dataclass(frozen=True, slots=True)
class ConsensusPolicy:
    minimum_experts: int = 2
    captaincy_fallback: CaptaincyFallback = "require_evidence"
    season: str | None = None
    gameweek: int | None = None


@dataclass(slots=True)
class _Votes:
    player: CataloguePlayer
    starter_experts: set[str]
    bench_experts: set[str]
    captain_experts: set[str]
    vice_experts: set[str]
    squad_experts: set[str]
    contributing_experts: set[str]
    confidence_by_expert: dict[str, float]

    @property
    def starter_support(self) -> int:
        return len(self.starter_experts)

    @property
    def bench_support(self) -> int:
        return len(self.bench_experts)

    @property
    def squad_support(self) -> int:
        return len(self.squad_experts)

    @property
    def captain_support(self) -> int:
        return len(self.captain_experts)

    @property
    def vice_support(self) -> int:
        return len(self.vice_experts)

    @property
    def confidence_sum(self) -> float:
        return round(sum(self.confidence_by_expert.values()), 4)


@dataclass(frozen=True, slots=True)
class _EligibleReveal:
    reveal: ExpertTeamRevealItem
    expert_id: str
    resolved_starters: frozenset[int]
    resolved_bench: frozenset[int]
    resolved_squad: frozenset[int]
    captain_id: int | None
    vice_id: int | None


def construct_consensus_squad(
    reveals: Sequence[ExpertTeamRevealItem],
    player_catalogue: PlayerCatalogue | Iterable[CataloguePlayer] | None,
    policy: ConsensusPolicy | None = None,
) -> SuggestedTeam:
    """Construct a deterministic 15-player squad from distinct-expert votes."""
    policy = policy or ConsensusPolicy()
    catalogue = _coerce_catalogue(player_catalogue)
    if catalogue is None or not catalogue:
        return _failure(FAILURE_MISSING_CATALOGUE)

    eligible = _eligible_reveals(reveals, catalogue, policy)
    expert_ids = {item.expert_id for item in eligible}
    provenance = _provenance(eligible)
    if len(expert_ids) < policy.minimum_experts:
        return _failure(
            FAILURE_TOO_FEW_EXPERTS,
            eligible_count=len(eligible),
            provenance=provenance,
        )

    votes = _aggregate_votes(eligible, catalogue)
    available = Counter(item.player.position for item in votes.values())
    if any(available[position] < quota for position, quota in SQUAD_QUOTAS.items()):
        return _failure(
            FAILURE_INSUFFICIENT_PLAYERS,
            eligible_count=len(eligible),
            provenance=provenance,
        )

    candidates: list[
        tuple[tuple[int, int, float, int], int, str, list[_Votes], list[_Votes]]
    ] = []
    for formation_index, (formation, quotas) in enumerate(FORMATION_ORDER):
        starters = _select_starters(votes.values(), quotas)
        if len(starters) != 11 or len({v.player.official_player_id for v in starters}) != 11:
            continue
        bench = _select_bench(votes.values(), starters, quotas)
        if len(bench) != 4:
            continue
        score = (
            sum(item.starter_support for item in starters),
            sum(item.captain_support for item in starters),
            round(sum(item.confidence_sum for item in starters), 4),
            sum(item.squad_support for item in (*starters, *bench)),
        )
        candidates.append((score, -formation_index, formation, starters, bench))

    if not candidates:
        # Positional coverage exists, so the more precise failure is formation/squad.
        reason = (
            FAILURE_NO_FORMATION
            if not any(
                len(_select_starters(votes.values(), quotas)) == 11
                for _, quotas in FORMATION_ORDER
            )
            else FAILURE_NO_SQUAD
        )
        return _failure(reason, eligible_count=len(eligible), provenance=provenance)

    _, _, formation, starters, bench = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    captain = _select_captain(starters, policy)
    if captain is None:
        return _failure(
            FAILURE_NO_CAPTAINCY,
            eligible_count=len(eligible),
            provenance=provenance,
        )
    vice = min(
        (item for item in starters if item is not captain),
        key=_vice_rank,
    )

    starter_players = [
        _output_player(item, is_starter=True, order=index)
        for index, item in enumerate(starters, start=1)
    ]
    bench_players = [
        _output_player(item, is_starter=False, order=index)
        for index, item in enumerate(bench, start=1)
    ]
    captain_id = captain.player.official_player_id
    vice_id = vice.player.official_player_id
    for player in (*starter_players, *bench_players):
        player.captain = player.playerId == captain_id
        player.viceCaptain = player.playerId == vice_id

    result = SuggestedTeam(
        constructionStatus="consensus",
        failureReason=None,
        eligibleRevealCount=len(eligible),
        contributingReveals=provenance,
        formation=formation,
        startingXi=starter_players,
        bench=bench_players,
        players=[*starter_players, *bench_players],
        captainPlayerId=captain_id,
        viceCaptainPlayerId=vice_id,
    )
    if not validate_consensus_squad(result):
        return _failure(
            FAILURE_NO_SQUAD,
            eligible_count=len(eligible),
            provenance=provenance,
        )
    return result


def build_suggested_team_from_reveals(
    reveals: list[ExpertTeamRevealItem],
    player_catalogue: PlayerCatalogue | Iterable[CataloguePlayer] | None = None,
    policy: ConsensusPolicy | None = None,
) -> SuggestedTeam:
    """Compatibility entry point for report synthesis."""
    return construct_consensus_squad(reveals, player_catalogue, policy)


def build_explicit_position_catalog(
    reveals: list[ExpertTeamRevealItem],
) -> dict[str, str]:
    """Legacy annotation helper; its output is never an authoritative catalogue."""
    catalog: dict[str, str] = {}
    conflicts: set[str] = set()
    for reveal in reveals:
        entries = list(reveal.player_positions.items())
        entries.extend(
            (name[: match.start()].strip(), match.group(1).upper())
            for name in reveal.current_team
            if (match := POSITION_SUFFIX.search(name)) is not None
        )
        for raw_name, position in entries:
            name = normalize_team_player(raw_name)
            if not name:
                continue
            if name in catalog and catalog[name] != position:
                conflicts.add(name)
            else:
                catalog[name] = position
    for name in conflicts:
        catalog.pop(name, None)
    return catalog


def validate_consensus_squad(team: SuggestedTeam) -> bool:
    if team.constructionStatus != "consensus" or team.failureReason is not None:
        return False
    if len(team.startingXi) != 11 or len(team.bench) != 4:
        return False
    players = [*team.startingXi, *team.bench]
    if len({item.officialPlayerId for item in players}) != 15:
        return False
    if Counter(item.position for item in players) != Counter(SQUAD_QUOTAS):
        return False
    starter_counts = Counter(item.position for item in team.startingXi)
    formation = f"{starter_counts['DEF']}-{starter_counts['MID']}-{starter_counts['FWD']}"
    if starter_counts["GK"] != 1 or formation != team.formation:
        return False
    starter_ids = {item.officialPlayerId for item in team.startingXi}
    return (
        team.captainPlayerId in starter_ids
        and team.viceCaptainPlayerId in starter_ids
        and team.captainPlayerId != team.viceCaptainPlayerId
    )


def _coerce_catalogue(
    value: PlayerCatalogue | Iterable[CataloguePlayer] | None,
) -> PlayerCatalogue | None:
    if value is None or isinstance(value, PlayerCatalogue):
        return value
    return PlayerCatalogue(value)


def _eligible_reveals(
    reveals: Sequence[ExpertTeamRevealItem],
    catalogue: PlayerCatalogue,
    policy: ConsensusPolicy,
) -> list[_EligibleReveal]:
    eligible: list[_EligibleReveal] = []
    seen_sources: set[tuple[str, str]] = set()
    ordered = sorted(
        reveals,
        key=lambda item: (
            item.expert_id or "",
            item.source_id or item.source_url or item.video_title,
            -(item.confidence or 0.0),
            _resolved_reveal_signature(item, catalogue),
        ),
    )
    for reveal in ordered:
        expert_id = (reveal.expert_id or "").strip()
        if not expert_id:
            continue
        if policy.season is not None and reveal.season != policy.season:
            continue
        if policy.gameweek is not None and reveal.gameweek != policy.gameweek:
            continue
        source_identity = reveal.source_id or reveal.source_url or reveal.video_title
        source_key = (expert_id, source_identity)
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        starters = _resolve_slot(reveal.starting_xi, reveal, catalogue)
        bench = _resolve_slot(reveal.bench, reveal, catalogue)
        squad = starters | bench | _resolve_slot(
            reveal.current_team, reveal, catalogue
        )
        if not squad:
            continue
        captain = _resolve_single(reveal.captain, reveal, catalogue)
        vice = _resolve_single(reveal.vice_captain, reveal, catalogue)
        eligible.append(
            _EligibleReveal(
                reveal=reveal,
                expert_id=expert_id,
                resolved_starters=frozenset(starters),
                resolved_bench=frozenset(bench),
                resolved_squad=frozenset(squad),
                captain_id=captain,
                vice_id=vice,
            )
        )
    return eligible


def _resolved_reveal_signature(
    reveal: ExpertTeamRevealItem,
    catalogue: PlayerCatalogue,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], int, int]:
    starters = _resolve_slot(reveal.starting_xi, reveal, catalogue)
    bench = _resolve_slot(reveal.bench, reveal, catalogue)
    squad = starters | bench | _resolve_slot(reveal.current_team, reveal, catalogue)
    return (
        tuple(sorted(starters)),
        tuple(sorted(bench)),
        tuple(sorted(squad)),
        _resolve_single(reveal.captain, reveal, catalogue) or 0,
        _resolve_single(reveal.vice_captain, reveal, catalogue) or 0,
    )


def _resolve_slot(
    names: Iterable[str],
    reveal: ExpertTeamRevealItem,
    catalogue: PlayerCatalogue,
) -> set[int]:
    resolved: set[int] = set()
    annotations = {
        normalize_team_player(name): position
        for name, position in reveal.player_positions.items()
    }
    for name in names:
        player = catalogue.resolve(name)
        if player is None:
            continue
        annotation = annotations.get(normalize_team_player(name))
        if annotation is not None and annotation != player.position:
            continue
        resolved.add(player.official_player_id)
    return resolved


def _resolve_single(
    name: str | None,
    reveal: ExpertTeamRevealItem,
    catalogue: PlayerCatalogue,
) -> int | None:
    return next(iter(_resolve_slot([name], reveal, catalogue)), None) if name else None


def _aggregate_votes(
    eligible: Sequence[_EligibleReveal],
    catalogue: PlayerCatalogue,
) -> dict[int, _Votes]:
    votes: dict[int, _Votes] = {}
    for item in eligible:
        all_ids = item.resolved_squad
        for player_id in all_ids:
            player = catalogue.by_id(player_id)
            if player is None:
                continue
            metric = votes.setdefault(
                player_id,
                _Votes(player, set(), set(), set(), set(), set(), set(), {}),
            )
            metric.squad_experts.add(item.expert_id)
            metric.contributing_experts.add(item.expert_id)
            confidence = item.reveal.confidence or 0.0
            metric.confidence_by_expert[item.expert_id] = max(
                confidence, metric.confidence_by_expert.get(item.expert_id, 0.0)
            )
            if player_id in item.resolved_starters:
                metric.starter_experts.add(item.expert_id)
            if player_id in item.resolved_bench:
                metric.bench_experts.add(item.expert_id)
            if player_id == item.captain_id and player_id in item.resolved_starters:
                metric.captain_experts.add(item.expert_id)
            if player_id == item.vice_id and player_id in item.resolved_starters:
                metric.vice_experts.add(item.expert_id)
    for metric in votes.values():
        # Contradictory repeated reveals from one expert cannot create two role votes.
        metric.bench_experts.difference_update(metric.starter_experts)
    return votes


def _starter_rank(item: _Votes) -> tuple[int, int, float, int]:
    return (
        -item.starter_support,
        -item.captain_support,
        -item.confidence_sum,
        item.player.official_player_id,
    )


def _bench_rank(item: _Votes) -> tuple[int, int, int, float, int]:
    return (
        -item.squad_support,
        -item.bench_support,
        -item.starter_support,
        -item.confidence_sum,
        item.player.official_player_id,
    )


def _select_starters(
    votes: Iterable[_Votes], quotas: Mapping[Position, int]
) -> list[_Votes]:
    selected: list[_Votes] = []
    pool = list(votes)
    for position in ("GK", "DEF", "MID", "FWD"):
        ranked = sorted(
            (item for item in pool if item.player.position == position),
            key=_starter_rank,
        )
        selected.extend(ranked[: quotas[position]])
    return selected


def _select_bench(
    votes: Iterable[_Votes],
    starters: Sequence[_Votes],
    starter_quotas: Mapping[Position, int],
) -> list[_Votes]:
    starter_ids = {item.player.official_player_id for item in starters}
    selected: list[_Votes] = []
    pool = list(votes)
    for position in ("GK", "DEF", "MID", "FWD"):
        needed = SQUAD_QUOTAS[position] - starter_quotas[position]
        ranked = sorted(
            (
                item
                for item in pool
                if item.player.position == position
                and item.player.official_player_id not in starter_ids
            ),
            key=_bench_rank,
        )
        selected.extend(ranked[:needed])
    return sorted(selected, key=_bench_rank)


def _captain_rank(item: _Votes) -> tuple[int, int, float, int]:
    return (
        -item.captain_support,
        -item.starter_support,
        -item.confidence_sum,
        item.player.official_player_id,
    )


def _vice_rank(item: _Votes) -> tuple[int, int, int, float, int]:
    return (
        -item.vice_support,
        -item.captain_support,
        -item.starter_support,
        -item.confidence_sum,
        item.player.official_player_id,
    )


def _select_captain(
    starters: Sequence[_Votes], policy: ConsensusPolicy
) -> _Votes | None:
    if any(item.captain_support for item in starters):
        return min(starters, key=_captain_rank)
    if policy.captaincy_fallback == "starter_support":
        return min(starters, key=_starter_rank)
    return None


def _output_player(item: _Votes, *, is_starter: bool, order: int) -> SuggestedPlayer:
    player = item.player
    return SuggestedPlayer(
        playerId=player.official_player_id,
        officialPlayerId=player.official_player_id,
        name=player.canonical_name,
        canonicalName=player.canonical_name,
        number=order if is_starter else None,
        position=player.position,
        club=player.club,
        price=player.price,
        expertSupportCount=item.squad_support,
        starterSupport=item.starter_support,
        benchSupport=item.bench_support,
        captainSupport=item.captain_support,
        viceCaptainSupport=item.vice_support,
        confidenceSum=item.confidence_sum,
        contributingExpertIds=sorted(item.contributing_experts),
        isStarter=is_starter,
        benchOrder=None if is_starter else order,
    )


def _provenance(eligible: Sequence[_EligibleReveal]) -> list[ContributingReveal]:
    unique: dict[tuple[str, str], ContributingReveal] = {}
    for item in eligible:
        reveal = item.reveal
        source_key = reveal.source_id or reveal.source_url or reveal.video_title
        unique[(item.expert_id, source_key)] = ContributingReveal(
            expertId=item.expert_id,
            expertName=reveal.expert_name,
            sourceId=reveal.source_id,
            sourceUrl=reveal.source_url,
            confidence=reveal.confidence or 0.0,
        )
    return [unique[key] for key in sorted(unique)]


def _failure(
    reason: str,
    *,
    eligible_count: int = 0,
    provenance: list[ContributingReveal] | None = None,
) -> SuggestedTeam:
    return SuggestedTeam(
        constructionStatus="insufficient_evidence",
        failureReason=reason,
        eligibleRevealCount=eligible_count,
        contributingReveals=provenance or [],
        formation=None,
        startingXi=[],
        bench=[],
        players=[],
    )


__all__ = [
    "CataloguePlayer",
    "ConsensusPolicy",
    "FORMATION_ORDER",
    "PlayerCatalogue",
    "build_suggested_team_from_reveals",
    "build_explicit_position_catalog",
    "construct_consensus_squad",
    "validate_consensus_squad",
]
