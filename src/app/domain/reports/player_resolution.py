from __future__ import annotations

from dataclasses import dataclass
import re

from rapidfuzz import fuzz

from src.app.domain.reports.player_catalogue import (
    FUZZY_SCORER,
    MIN_FUZZY_MARGIN,
    MIN_FUZZY_REFERENCE_LENGTH,
    MIN_FUZZY_SCORE,
    CataloguePlayer,
    PlayerCatalogue,
    normalise_player_name,
)
from src.schemas.player_resolution import (
    CanonicalPlayerResult,
    ExtractedPlayerInput,
    FuzzyMatchDiagnostic,
    PlayerResolutionEvent,
    ResolutionSource,
    normalise_extracted_reference,
)


INITIALS_ONLY = re.compile(r"^(?:[a-z]\s*){1,4}$")


@dataclass(frozen=True, slots=True)
class Resolution:
    player: CataloguePlayer | None
    event: PlayerResolutionEvent


class PlayerResolver:
    def __init__(self, catalogue: PlayerCatalogue) -> None:
        self.catalogue = catalogue

    def resolve(
        self,
        raw: ExtractedPlayerInput,
        *,
        source: ResolutionSource,
        extracted_position: str | None = None,
    ) -> Resolution:
        reference = normalise_extracted_reference(raw)
        position_hint = reference.positionHint or extracted_position
        warnings: list[str] = []
        if reference.playerId is not None:
            by_id = self.catalogue.by_id(reference.playerId)
            if by_id is None:
                return self._rejected(
                    reference,
                    source,
                    "unknown_player_id",
                    position_hint=position_hint,
                )
            name_resolution = self._resolve_name(
                reference.name, club_hint=reference.clubHint
            )
            if (
                name_resolution.player is not None
                and name_resolution.player.official_player_id
                != by_id.official_player_id
            ):
                return self._rejected(
                    reference,
                    source,
                    "player_id_name_conflict",
                    position_hint=position_hint,
                    candidates=name_resolution.candidates,
                    conflicting_id=name_resolution.player.official_player_id,
                    match=name_resolution.match,
                )
            if name_resolution.player is None:
                warnings.append("unverified_name_for_player_id")
            return self._resolved(
                reference,
                source,
                by_id,
                method="player_id",
                warnings=warnings,
                position_hint=position_hint,
                candidates=(
                    name_resolution.candidates
                    if name_resolution.candidates
                    else [by_id.official_player_id]
                ),
                match=name_resolution.match,
            )

        name_resolution = self._resolve_name(
            reference.name, club_hint=reference.clubHint
        )
        if name_resolution.player is None:
            return self._rejected(
                reference,
                source,
                name_resolution.reason or "unresolved_player_name",
                position_hint=position_hint,
                candidates=name_resolution.candidates,
                match=name_resolution.match,
            )
        return self._resolved(
            reference,
            source,
            name_resolution.player,
            method=name_resolution.method or "fuzzy",
            warnings=warnings,
            position_hint=position_hint,
            candidates=name_resolution.candidates,
            match=name_resolution.match,
        )

    def _resolved(
        self,
        reference,
        source,
        player: CataloguePlayer,
        *,
        method: str,
        warnings: list[str],
        position_hint: str | None,
        candidates: list[int],
        match: FuzzyMatchDiagnostic | None,
    ) -> Resolution:
        if position_hint and position_hint != str(player.position):
            warnings.append("position_mismatch")
        event = PlayerResolutionEvent(
            rawName=reference.name,
            rawPlayerId=reference.playerId,
            clubHint=reference.clubHint,
            extractedPosition=position_hint,
            source=source,
            status="resolved",
            canonicalPlayerId=player.official_player_id,
            canonicalResult=CanonicalPlayerResult(
                playerId=player.official_player_id,
                displayName=player.display_name or player.canonical_name,
                club=player.club,
                position=str(player.position),
            ),
            method=method,
            warnings=warnings,
            match=match,
            candidatePlayerIds=sorted(set(candidates)),
        )
        return Resolution(player, event)

    def _rejected(
        self,
        reference,
        source,
        reason: str,
        *,
        position_hint: str | None,
        candidates: list[int] | None = None,
        conflicting_id: int | None = None,
        match: FuzzyMatchDiagnostic | None = None,
    ) -> Resolution:
        return Resolution(
            None,
            PlayerResolutionEvent(
                rawName=reference.name,
                rawPlayerId=reference.playerId,
                clubHint=reference.clubHint,
                extractedPosition=position_hint,
                source=source,
                status="rejected",
                reason=reason,
                conflictingPlayerId=conflicting_id,
                match=match,
                candidatePlayerIds=sorted(set(candidates or [])),
            ),
        )

    def _resolve_name(self, name: str, *, club_hint: str | None) -> "_NameResult":
        normalized = normalise_player_name(name)
        if not normalized:
            return _NameResult(reason="unresolved_player_name")
        viable_ids = {
            player.official_player_id
            for player in self.catalogue.players
            if not club_hint
            or normalise_player_name(player.club) == normalise_player_name(club_hint)
        }
        exact_ids = [
            player_id
            for player_id in self.catalogue.exact_candidate_ids(name)
            if player_id in viable_ids
        ]
        if len(exact_ids) == 1:
            player = self.catalogue.by_id(exact_ids[0])
            assert player is not None
            method = self._exact_method(normalized, exact_ids[0])
            return _NameResult(player, method, candidates=exact_ids)
        if len(exact_ids) > 1:
            return _NameResult(reason="ambiguous_player_name", candidates=exact_ids)

        short = len(normalized.replace(" ", "")) < MIN_FUZZY_REFERENCE_LENGTH
        initials_only = bool(INITIALS_ONLY.fullmatch(normalized))
        if short or initials_only:
            # A short exact reference is only safe when a club hint uniquely narrows it.
            token_matches = sorted(
                {
                    player_id
                    for field, player_id, _ in self.catalogue.candidate_fields
                    if player_id in viable_ids
                    and normalized in field.split()
                }
            )
            if club_hint and len(token_matches) == 1:
                player = self.catalogue.by_id(token_matches[0])
                assert player is not None
                return _NameResult(
                    player, self._exact_method(normalized, token_matches[0]),
                    candidates=token_matches,
                )
            return _NameResult(
                reason=(
                    "initials_only_reference"
                    if initials_only
                    else "reference_too_short"
                ),
                candidates=token_matches,
            )

        best_by_player: dict[int, tuple[float, str]] = {}
        for field, player_id, field_name in self.catalogue.candidate_fields:
            if player_id not in viable_ids:
                continue
            score = float(fuzz.WRatio(normalized, field))
            prior = best_by_player.get(player_id)
            if prior is None or (score, field_name) > (prior[0], prior[1]):
                best_by_player[player_id] = (score, field_name)
        ranked = sorted(
            (
                (score, player_id, field_name)
                for player_id, (score, field_name) in best_by_player.items()
            ),
            key=lambda item: (-item[0], item[1], item[2]),
        )
        if not ranked:
            return _NameResult(reason="unresolved_player_name")
        best_score, best_id, matched_field = ranked[0]
        runner_score = ranked[1][0] if len(ranked) > 1 else None
        margin = (
            round(best_score - runner_score, 4)
            if runner_score is not None
            else None
        )
        diagnostic = FuzzyMatchDiagnostic(
            algorithm=FUZZY_SCORER,
            score=round(best_score, 4),
            runnerUpScore=(
                round(runner_score, 4) if runner_score is not None else None
            ),
            margin=margin,
            matchedField=matched_field,
        )
        candidate_ids = [item[1] for item in ranked]
        if best_score < MIN_FUZZY_SCORE:
            return _NameResult(
                reason="fuzzy_score_below_threshold",
                candidates=candidate_ids,
                match=diagnostic,
            )
        if runner_score is not None and (
            best_score == runner_score or margin is None or margin < MIN_FUZZY_MARGIN
        ):
            return _NameResult(
                reason="ambiguous_fuzzy_match",
                candidates=candidate_ids,
                match=diagnostic,
            )
        player = self.catalogue.by_id(best_id)
        assert player is not None
        return _NameResult(
            player,
            "fuzzy",
            candidates=candidate_ids,
            match=diagnostic,
        )

    def _exact_method(self, normalized: str, player_id: int) -> str:
        player = self.catalogue.by_id(player_id)
        assert player is not None
        if normalized == normalise_player_name(player.canonical_name):
            return "canonical_full_name"
        if normalized == normalise_player_name(player.display_name):
            return "canonical_display_name"
        return "alias"


@dataclass(slots=True)
class _NameResult:
    player: CataloguePlayer | None = None
    method: str | None = None
    reason: str | None = None
    candidates: list[int] = None  # type: ignore[assignment]
    match: FuzzyMatchDiagnostic | None = None

    def __post_init__(self) -> None:
        if self.candidates is None:
            self.candidates = []


__all__ = ["PlayerResolver", "Resolution"]
