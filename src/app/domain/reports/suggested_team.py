from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from statistics import median
from typing import Any, Literal

from src.app.domain.reports.player_catalogue import (
    CatalogueError,
    CataloguePlayer,
    PlayerCatalogue,
    Position,
)
from src.app.domain.reports.player_resolution import PlayerResolver
from src.app.domain.reports.team_of_week import normalize_team_player
from src.schemas.aggregate_report import ExpertTeamRevealItem
from src.schemas.final_report import (
    ConsensusStrengthBasis,
    ContributingExpert,
    ContributingReveal,
    ExcludedReveal,
    FormationDerivation,
    PlayerSupport,
    SuggestedPlayer,
    SuggestedTeam,
    SuggestedTeamProvenance,
)
from src.schemas.player_resolution import (
    ExtractedPlayerInput,
    PlayerResolutionEvent,
    ResolutionSource,
    normalise_extracted_reference,
)


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
    resolution_events: tuple[PlayerResolutionEvent, ...]
    captaincy_validation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _EligibilityResult:
    eligible_reveals: tuple[_EligibleReveal, ...]
    contributing_reveals: tuple[_EligibleReveal, ...]
    exclusions: tuple[ExcludedReveal, ...]


def construct_consensus_squad(
    reveals: Sequence[ExpertTeamRevealItem],
    player_catalogue: PlayerCatalogue | Iterable[CataloguePlayer] | CatalogueError | None,
    policy: ConsensusPolicy | None = None,
) -> SuggestedTeam:
    """Construct a deterministic 15-player squad from distinct-expert votes."""
    policy = policy or ConsensusPolicy()
    if isinstance(player_catalogue, CatalogueError):
        return _failure(player_catalogue.reason)
    catalogue = _coerce_catalogue(player_catalogue)
    if catalogue is None or not catalogue:
        return _failure(FAILURE_MISSING_CATALOGUE)

    eligibility = _eligible_reveals(reveals, catalogue, policy)
    resolved_reveals = list(eligibility.eligible_reveals)
    eligible = list(eligibility.contributing_reveals)
    expert_ids = {item.expert_id for item in eligible}
    provenance = _provenance(eligible)
    diagnostics = [
        event for item in resolved_reveals for event in item.resolution_events
    ]
    captaincy_validation = sorted(
        {
            outcome
            for item in resolved_reveals
            for outcome in item.captaincy_validation
        }
    )
    if not expert_ids:
        return _failure(
            FAILURE_TOO_FEW_EXPERTS,
            eligible_reveal_count=len(resolved_reveals),
            eligible_expert_count=0,
            provenance=provenance,
            excluded_reveals=list(eligibility.exclusions),
            diagnostics=diagnostics,
            catalogue=catalogue,
            captaincy_validation=captaincy_validation,
        )

    votes = _aggregate_votes(eligible, catalogue)
    available = Counter(item.player.position for item in votes.values())
    if any(available[position] < quota for position, quota in SQUAD_QUOTAS.items()):
        return _failure(
            FAILURE_INSUFFICIENT_PLAYERS,
            eligible_reveal_count=len(resolved_reveals),
            eligible_expert_count=len(expert_ids),
            provenance=provenance,
            excluded_reveals=list(eligibility.exclusions),
            diagnostics=diagnostics,
            catalogue=catalogue,
            captaincy_validation=captaincy_validation,
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
        return _failure(
            reason,
            eligible_reveal_count=len(resolved_reveals),
            eligible_expert_count=len(expert_ids),
            provenance=provenance,
            excluded_reveals=list(eligibility.exclusions),
            diagnostics=diagnostics,
            catalogue=catalogue,
            captaincy_validation=captaincy_validation,
        )

    _, _, formation, starters, bench = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    captain = _select_captain(starters, policy)
    if captain is None:
        return _failure(
            FAILURE_NO_CAPTAINCY,
            eligible_reveal_count=len(resolved_reveals),
            eligible_expert_count=len(expert_ids),
            provenance=provenance,
            excluded_reveals=list(eligibility.exclusions),
            diagnostics=diagnostics,
            catalogue=catalogue,
            captaincy_validation=captaincy_validation,
        )
    vice = min(
        (item for item in starters if item is not captain),
        key=_vice_rank,
    )

    starter_players = [
        _output_player(
            item,
            is_starter=True,
            order=index,
            eligible_expert_count=len(expert_ids),
        )
        for index, item in enumerate(starters, start=1)
    ]
    bench_players = [
        _output_player(
            item,
            is_starter=False,
            order=index,
            eligible_expert_count=len(expert_ids),
        )
        for index, item in enumerate(bench, start=1)
    ]
    captain_id = captain.player.official_player_id
    vice_id = vice.player.official_player_id
    for player in (*starter_players, *bench_players):
        player.captain = player.playerId == captain_id
        player.viceCaptain = player.playerId == vice_id

    construction_method = (
        "vote_based_consensus" if len(expert_ids) >= 2 else "single_reveal"
    )
    strength, strength_basis = _consensus_strength(
        starter_players,
        eligible_expert_count=len(expert_ids),
        valid_lineup=True,
        construction_method=construction_method,
    )
    formation_derivation = FormationDerivation(
        method="selected_starting_xi_positions",
        formation=formation,
        positionSource="authoritative_player_catalogue",
        authoritativeCataloguePositions=True,
        fallbackApplied=None,
    )
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    contributing_experts = _contributing_experts(eligible)
    snapshot_provenance = SuggestedTeamProvenance(
        constructionMethod=construction_method,
        generatedAt=generated_at,
        eligibleRevealCount=len(resolved_reveals),
        eligibleExpertCount=len(expert_ids),
        contributingRevealCount=len(eligible),
        contributingExperts=contributing_experts,
        excludedRevealCount=len(eligibility.exclusions),
        excludedReveals=list(eligibility.exclusions),
        formationDerivation=formation_derivation,
        consensusStrength=strength,
        consensusStrengthBasis=strength_basis,
    )
    result = SuggestedTeam(
        constructionStatus="consensus",
        constructionMethod=construction_method,
        consensusStrength=strength,
        provenanceAvailable=True,
        provenance=snapshot_provenance,
        failureReason=None,
        eligibleRevealCount=len(resolved_reveals),
        eligibleExpertCount=len(expert_ids),
        contributingReveals=provenance,
        formation=formation,
        startingXi=starter_players,
        bench=bench_players,
        players=[*starter_players, *bench_players],
        captainPlayerId=captain_id,
        viceCaptainPlayerId=vice_id,
        catalogueSeason=catalogue.season,
        catalogueSource=catalogue.source,
        catalogueFingerprint=catalogue.fingerprint,
        warnings=sorted(
            {
                warning
                for event in diagnostics
                for warning in event.warnings
            }
        ),
        captaincyValidation=captaincy_validation,
        resolutionDiagnostics=diagnostics,
    )
    if not validate_consensus_squad(result):
        return _failure(
            FAILURE_NO_SQUAD,
            eligible_reveal_count=len(resolved_reveals),
            eligible_expert_count=len(expert_ids),
            provenance=provenance,
            excluded_reveals=list(eligibility.exclusions),
            diagnostics=diagnostics,
            catalogue=catalogue,
            captaincy_validation=captaincy_validation,
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
            (reference.name[: match.start()].strip(), match.group(1).upper())
            for value in reveal.current_team
            if (
                reference := normalise_extracted_reference(value)
            ) is not None
            and (match := POSITION_SUFFIX.search(reference.name)) is not None
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
) -> _EligibilityResult:
    eligible: list[_EligibleReveal] = []
    contributing: list[_EligibleReveal] = []
    exclusions: list[ExcludedReveal] = []
    seen_sources: set[str] = set()
    seen_experts: set[str] = set()
    valid_reveals: list[ExpertTeamRevealItem] = []
    for raw_reveal in reveals:
        if isinstance(raw_reveal, ExpertTeamRevealItem):
            valid_reveals.append(raw_reveal)
        else:
            exclusions.append(
                _excluded_raw_reveal(
                    raw_reveal,
                    (
                        "invalid_reveal_structure"
                        if isinstance(raw_reveal, Mapping)
                        else "unsupported_reveal_type"
                    ),
                )
            )
    ordered = sorted(
        valid_reveals,
        key=lambda item: (
            -(item.confidence or 0.0),
            item.expert_id or "",
            item.source_id or item.source_url or item.video_title,
            json.dumps(item.model_dump(mode="json"), sort_keys=True),
        ),
    )
    resolver = PlayerResolver(catalogue)
    for reveal in ordered:
        expert_id = (reveal.expert_id or "").strip()
        if not expert_id:
            exclusions.append(_excluded_reveal(reveal, "missing_expert_identity"))
            continue
        if policy.season is not None and reveal.season != policy.season:
            exclusions.append(_excluded_reveal(reveal, "wrong_season"))
            continue
        if policy.gameweek is not None and reveal.gameweek != policy.gameweek:
            exclusions.append(_excluded_reveal(reveal, "wrong_gameweek"))
            continue
        source_identity = reveal.source_id or reveal.source_url or reveal.video_title
        if source_identity in seen_sources:
            exclusions.append(_excluded_reveal(reveal, "duplicate_source"))
            continue
        seen_sources.add(source_identity)

        starters, starter_events = _resolve_slot(
            reveal.starting_xi, reveal, resolver, "starter"
        )
        bench, bench_events = _resolve_slot(
            reveal.bench, reveal, resolver, "bench", already_seen=starters
        )
        current, current_events = _resolve_slot(
            reveal.current_team,
            reveal,
            resolver,
            "current_team",
            already_seen=starters | bench,
        )
        squad = starters | bench | current
        captain, captain_events = _resolve_single(
            reveal.captain, reveal, resolver, "captain"
        )
        vice, vice_events = _resolve_single(
            reveal.vice_captain, reveal, resolver, "vice_captain"
        )
        captaincy_validation: list[str] = []
        if reveal.captain is not None and captain is None:
            captaincy_validation.append("unresolved_captain")
        if reveal.vice_captain is not None and vice is None:
            captaincy_validation.append("unresolved_vice_captain")
        if captain is not None and captain not in starters:
            captaincy_validation.append("captain_not_in_starting_xi")
            captain = None
        if vice is not None and vice not in starters:
            captaincy_validation.append("vice_captain_not_in_starting_xi")
            vice = None
        if captain is not None and captain == vice:
            captaincy_validation.append("duplicate_captain_and_vice")
            captain = None
            vice = None
        item = _EligibleReveal(
            reveal=reveal,
            expert_id=expert_id,
            resolved_starters=frozenset(starters),
            resolved_bench=frozenset(bench),
            resolved_squad=frozenset(squad),
            captain_id=captain,
            vice_id=vice,
            resolution_events=tuple(
                [
                    *starter_events,
                    *bench_events,
                    *current_events,
                    *captain_events,
                    *vice_events,
                ]
            ),
            captaincy_validation=tuple(captaincy_validation),
        )
        if not item.resolved_squad:
            exclusions.append(_excluded_reveal(reveal, "empty_resolved_squad"))
            continue
        if len(item.resolved_squad) < 11:
            exclusions.append(
                _excluded_reveal(
                    reveal,
                    "insufficient_resolved_players",
                    detail=(
                        f"Resolved {len(item.resolved_squad)} distinct players; "
                        "at least 11 are required."
                    ),
                )
            )
            continue
        eligible.append(item)
        if expert_id in seen_experts:
            exclusions.append(_excluded_reveal(reveal, "duplicate_expert_reveal"))
            continue
        seen_experts.add(expert_id)
        contributing.append(item)
    return _EligibilityResult(
        eligible_reveals=tuple(eligible),
        contributing_reveals=tuple(contributing),
        exclusions=tuple(exclusions),
    )


def _reveal_id(reveal: ExpertTeamRevealItem) -> str:
    return reveal.source_id or reveal.source_url or reveal.video_title


def _excluded_reveal(
    reveal: ExpertTeamRevealItem,
    reason: str,
    *,
    detail: str | None = None,
) -> ExcludedReveal:
    return ExcludedReveal(
        revealId=_reveal_id(reveal),
        expertId=(reveal.expert_id or "").strip() or None,
        expertName=reveal.expert_name or None,
        sourceId=reveal.source_id,
        sourceTitle=reveal.video_title or None,
        reasons=[reason],
        detail=detail,
    )


def _excluded_raw_reveal(value: Any, reason: str) -> ExcludedReveal:
    raw = value if isinstance(value, Mapping) else {}
    source_id = raw.get("source_id")
    source_title = raw.get("video_title")
    return ExcludedReveal(
        revealId=str(source_id or source_title) if source_id or source_title else None,
        expertId=str(raw["expert_id"]) if raw.get("expert_id") else None,
        expertName=str(raw["expert_name"]) if raw.get("expert_name") else None,
        sourceId=str(source_id) if source_id else None,
        sourceTitle=str(source_title) if source_title else None,
        reasons=[reason],
        detail=f"Received {type(value).__name__}.",
    )


def _resolve_slot(
    values: Iterable[ExtractedPlayerInput],
    reveal: ExpertTeamRevealItem,
    resolver: PlayerResolver,
    role: Literal["starter", "bench", "current_team"],
    *,
    already_seen: set[int] | None = None,
) -> tuple[set[int], list[PlayerResolutionEvent]]:
    resolved: set[int] = set()
    events: list[PlayerResolutionEvent] = []
    seen = set(already_seen or ())
    annotations = {
        normalize_team_player(name): position
        for name, position in reveal.player_positions.items()
    }
    for value in values:
        reference = normalise_extracted_reference(value)
        annotation = annotations.get(normalize_team_player(reference.name))
        result = resolver.resolve(
            reference,
            source=ResolutionSource(
                expertId=reveal.expert_id,
                videoId=reveal.source_id or reveal.source_url or reveal.video_title,
                squadRole=role,
            ),
            extracted_position=annotation,
        )
        event = result.event
        if result.player is not None:
            player_id = result.player.official_player_id
            if player_id in seen or player_id in resolved:
                event = event.model_copy(
                    update={
                        "status": "duplicate",
                        "duplicateOfPlayerId": player_id,
                    }
                )
            else:
                resolved.add(player_id)
        events.append(event)
    return resolved, events


def _resolve_single(
    value: ExtractedPlayerInput | None,
    reveal: ExpertTeamRevealItem,
    resolver: PlayerResolver,
    role: Literal["captain", "vice_captain"],
) -> tuple[int | None, list[PlayerResolutionEvent]]:
    if value is None:
        return None, []
    reference = normalise_extracted_reference(value)
    result = resolver.resolve(
        reference,
        source=ResolutionSource(
            expertId=reveal.expert_id,
            videoId=reveal.source_id or reveal.source_url or reveal.video_title,
            squadRole=role,
        ),
        extracted_position=reveal.player_positions.get(reference.name),
    )
    return (
        result.player.official_player_id if result.player is not None else None,
        [result.event],
    )


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


def _percentage(count: int, denominator: int) -> float:
    return round((count / denominator) * 100, 1) if denominator else 0.0


def _output_player(
    item: _Votes,
    *,
    is_starter: bool,
    order: int,
    eligible_expert_count: int,
) -> SuggestedPlayer:
    player = item.player
    contributing_expert_ids = sorted(item.contributing_experts)
    return SuggestedPlayer(
        playerId=player.official_player_id,
        officialPlayerId=player.official_player_id,
        name=player.canonical_name,
        canonicalName=player.canonical_name,
        displayName=player.display_name,
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
        contributingExpertIds=contributing_expert_ids,
        support=PlayerSupport(
            eligibleExpertCount=eligible_expert_count,
            starterSupportCount=item.starter_support,
            starterSupportPercentage=_percentage(
                item.starter_support, eligible_expert_count
            ),
            squadSupportCount=item.squad_support,
            squadSupportPercentage=_percentage(
                item.squad_support, eligible_expert_count
            ),
            captainSupportCount=item.captain_support,
            captainSupportPercentage=_percentage(
                item.captain_support, eligible_expert_count
            ),
            viceCaptainSupportCount=item.vice_support,
            viceCaptainSupportPercentage=_percentage(
                item.vice_support, eligible_expert_count
            ),
            contributingExpertIds=contributing_expert_ids,
        ),
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


def _contributing_experts(
    eligible: Sequence[_EligibleReveal],
) -> list[ContributingExpert]:
    names: dict[str, str] = {}
    reveal_ids: dict[str, set[str]] = {}
    for item in eligible:
        names.setdefault(item.expert_id, item.reveal.expert_name)
        reveal_ids.setdefault(item.expert_id, set()).add(_reveal_id(item.reveal))
    return [
        ContributingExpert(
            expertId=expert_id,
            expertName=names[expert_id],
            revealIds=sorted(reveal_ids[expert_id]),
        )
        for expert_id in sorted(names)
    ]


def _experts_from_reveal_provenance(
    reveals: Sequence[ContributingReveal],
) -> list[ContributingExpert]:
    names: dict[str, str] = {}
    reveal_ids: dict[str, set[str]] = {}
    for reveal in reveals:
        names.setdefault(reveal.expertId, reveal.expertName)
        source = reveal.sourceId or reveal.sourceUrl
        if source:
            reveal_ids.setdefault(reveal.expertId, set()).add(source)
    return [
        ContributingExpert(
            expertId=expert_id,
            expertName=names[expert_id],
            revealIds=sorted(reveal_ids.get(expert_id, set())),
        )
        for expert_id in sorted(names)
    ]


def _consensus_strength(
    starters: Sequence[SuggestedPlayer],
    *,
    eligible_expert_count: int,
    valid_lineup: bool,
    construction_method: str,
) -> tuple[str, ConsensusStrengthBasis]:
    percentages = [
        player.support.starterSupportPercentage
        for player in starters
        if player.support is not None
    ]
    median_percentage = (
        round(float(median(percentages)), 1) if percentages else None
    )
    if (
        not valid_lineup
        or construction_method != "vote_based_consensus"
        or eligible_expert_count < 2
        or median_percentage is None
    ):
        strength = "insufficient"
    elif eligible_expert_count >= 3 and median_percentage >= 67:
        strength = "strong"
    elif median_percentage >= 50:
        strength = "moderate"
    else:
        strength = "split"
    return strength, ConsensusStrengthBasis(
        metric="median_starting_xi_support_percentage",
        medianSupportPercentage=median_percentage,
        minimumExpertRequirement=3,
    )


def _failure(
    reason: str,
    *,
    eligible_reveal_count: int = 0,
    eligible_expert_count: int = 0,
    provenance: list[ContributingReveal] | None = None,
    excluded_reveals: list[ExcludedReveal] | None = None,
    diagnostics: list[PlayerResolutionEvent] | None = None,
    catalogue: PlayerCatalogue | None = None,
    captaincy_validation: list[str] | None = None,
) -> SuggestedTeam:
    exclusions = excluded_reveals or []
    formation_derivation = FormationDerivation(
        method="selected_starting_xi_positions",
        formation=None,
        positionSource=(
            "authoritative_player_catalogue" if catalogue else "unavailable"
        ),
        authoritativeCataloguePositions=catalogue is not None,
        fallbackApplied=None,
    )
    basis = ConsensusStrengthBasis(
        metric="median_starting_xi_support_percentage",
        medianSupportPercentage=None,
        minimumExpertRequirement=3,
    )
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return SuggestedTeam(
        constructionStatus="insufficient_evidence",
        constructionMethod="insufficient_evidence",
        consensusStrength="insufficient",
        provenanceAvailable=True,
        provenance=SuggestedTeamProvenance(
            constructionMethod="insufficient_evidence",
            generatedAt=generated_at,
            eligibleRevealCount=eligible_reveal_count,
            eligibleExpertCount=eligible_expert_count,
            contributingRevealCount=len(provenance or []),
            contributingExperts=_experts_from_reveal_provenance(provenance or []),
            excludedRevealCount=len(exclusions),
            excludedReveals=exclusions,
            formationDerivation=formation_derivation,
            consensusStrength="insufficient",
            consensusStrengthBasis=basis,
        ),
        failureReason=reason,
        eligibleRevealCount=eligible_reveal_count,
        eligibleExpertCount=eligible_expert_count,
        contributingReveals=provenance or [],
        formation=None,
        startingXi=[],
        bench=[],
        players=[],
        catalogueSeason=catalogue.season if catalogue else None,
        catalogueSource=catalogue.source if catalogue else None,
        catalogueFingerprint=catalogue.fingerprint if catalogue else None,
        warnings=sorted(
            {
                warning
                for event in diagnostics or []
                for warning in event.warnings
            }
        ),
        captaincyValidation=captaincy_validation or [],
        resolutionDiagnostics=diagnostics or [],
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
