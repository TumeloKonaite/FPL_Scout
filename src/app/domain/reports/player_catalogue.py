from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Protocol

import rapidfuzz


NAME_NORMALISATION_VERSION = "fpl-name-v1"
FUZZY_SCORER = "rapidfuzz.fuzz.WRatio"
MIN_FUZZY_SCORE = 92.0
MIN_FUZZY_MARGIN = 5.0
MIN_FUZZY_REFERENCE_LENGTH = 5


class Position(StrEnum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


FPL_POSITION_TO_DOMAIN = {
    "GKP": Position.GK,
    "DEF": Position.DEF,
    "MID": Position.MID,
    "FWD": Position.FWD,
}


class CatalogueError(RuntimeError):
    reason = "catalogue_unavailable"


class CatalogueUnavailable(CatalogueError):
    reason = "catalogue_unavailable"


class CatalogueSeasonMismatch(CatalogueError):
    reason = "catalogue_season_mismatch"


class InvalidCatalogue(CatalogueError):
    pass


class UnknownFplPositionType(InvalidCatalogue):
    reason = "unknown_fpl_position_type"


class InvalidAliasConfiguration(InvalidCatalogue):
    reason = "invalid_alias_configuration"


@dataclass(frozen=True, slots=True)
class CataloguePlayer:
    official_player_id: int
    canonical_name: str
    position: Position | str
    club: str | None = None
    price: float | None = None
    aliases: tuple[str, ...] = ()
    display_name: str | None = None

    def __post_init__(self) -> None:
        try:
            position = Position(self.position)
        except ValueError as exc:
            raise UnknownFplPositionType(str(self.position)) from exc
        object.__setattr__(self, "position", position)
        object.__setattr__(
            self, "display_name", self.display_name or self.canonical_name
        )


@dataclass(frozen=True, slots=True)
class AliasConfiguration:
    season: str
    aliases: Mapping[int, Iterable[str]]


def load_alias_configuration(path: str | Path) -> AliasConfiguration:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidAliasConfiguration("invalid_alias_file") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("season"), str):
        raise InvalidAliasConfiguration("invalid_alias_file")
    aliases = raw.get("aliases")
    if not isinstance(aliases, dict):
        raise InvalidAliasConfiguration("invalid_alias_file")
    converted: dict[int, tuple[str, ...]] = {}
    try:
        for player_id, values in aliases.items():
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                raise ValueError
            converted[int(player_id)] = tuple(values)
    except (TypeError, ValueError) as exc:
        raise InvalidAliasConfiguration("invalid_alias_file") from exc
    return AliasConfiguration(raw["season"], converted)


def normalise_player_name(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).split())


class PlayerCatalogue:
    """Immutable, season-bound set of canonical FPL players."""

    def __init__(
        self,
        players: Iterable[CataloguePlayer],
        *,
        season: str | None = None,
        aliases: AliasConfiguration | Mapping[int, Iterable[str]] | None = None,
        source: str = "explicit",
    ) -> None:
        materialized = list(players)
        self.season = season
        self.source = source
        if isinstance(aliases, AliasConfiguration):
            if season is None or aliases.season != season:
                raise InvalidAliasConfiguration("alias_season_mismatch")
            configured_aliases = aliases.aliases
        else:
            configured_aliases = aliases or {}

        by_id: dict[int, CataloguePlayer] = {}
        for player in materialized:
            if player.official_player_id <= 0:
                raise InvalidCatalogue("invalid_player_id")
            if player.official_player_id in by_id:
                raise InvalidCatalogue("duplicate_player_id")
            by_id[player.official_player_id] = player

        unknown_alias_ids = set(configured_aliases) - set(by_id)
        if unknown_alias_ids:
            raise InvalidAliasConfiguration(
                f"alias_unknown_player_id:{min(unknown_alias_ids)}"
            )

        canonical_fields: dict[str, set[int]] = {}
        for player in by_id.values():
            for value in (player.canonical_name, player.display_name):
                key = normalise_player_name(value)
                if not key:
                    raise InvalidCatalogue("empty_canonical_player_name")
                canonical_fields.setdefault(key, set()).add(player.official_player_id)

        merged: dict[int, tuple[str, ...]] = {}
        alias_owner: dict[str, int] = {}
        for player_id, player in sorted(by_id.items()):
            raw_aliases = [*player.aliases, *configured_aliases.get(player_id, ())]
            normalized_for_player: set[str] = set()
            accepted: list[str] = []
            for alias in raw_aliases:
                key = normalise_player_name(alias)
                if not key:
                    raise InvalidAliasConfiguration("empty_alias")
                if key in normalized_for_player:
                    raise InvalidAliasConfiguration(
                        f"duplicate_normalised_alias:{alias}"
                    )
                normalized_for_player.add(key)
                canonical_owners = canonical_fields.get(key, set())
                if canonical_owners and canonical_owners != {player_id}:
                    raise InvalidAliasConfiguration(
                        f"alias_canonical_name_collision:{alias}"
                    )
                previous = alias_owner.get(key)
                if previous is not None and previous != player_id:
                    raise InvalidAliasConfiguration(f"ambiguous_alias:{alias}")
                alias_owner[key] = player_id
                accepted.append(alias)
            merged[player_id] = tuple(accepted)

        self._players = by_id
        self._aliases = merged
        exact: dict[str, set[int]] = {}
        fields: list[tuple[str, int, str]] = []
        for player_id, player in sorted(by_id.items()):
            values = (
                ("canonical_full_name", player.canonical_name),
                ("canonical_display_name", player.display_name or player.canonical_name),
                *(("alias", alias) for alias in merged[player_id]),
            )
            for field_name, value in values:
                key = normalise_player_name(value)
                exact.setdefault(key, set()).add(player_id)
                fields.append((key, player_id, field_name))
        self._exact = exact
        self._candidate_fields = tuple(sorted(set(fields)))
        self.fingerprint = self._build_fingerprint()

    @property
    def players(self) -> tuple[CataloguePlayer, ...]:
        return tuple(self._players[key] for key in sorted(self._players))

    def by_id(self, player_id: int) -> CataloguePlayer | None:
        return self._players.get(player_id)

    def exact_candidate_ids(self, name: str | None) -> tuple[int, ...]:
        return tuple(sorted(self._exact.get(normalise_player_name(name), ())))

    def aliases_for(self, player_id: int) -> tuple[str, ...]:
        return self._aliases.get(player_id, ())

    @property
    def candidate_fields(self) -> tuple[tuple[str, int, str], ...]:
        return self._candidate_fields

    def resolve(self, name: str | None) -> CataloguePlayer | None:
        ids = self.exact_candidate_ids(name)
        return self.by_id(ids[0]) if len(ids) == 1 else None

    def __bool__(self) -> bool:
        return bool(self._players)

    def _build_fingerprint(self) -> str:
        payload = {
            "season": self.season,
            "players": [
                {
                    "playerId": item.official_player_id,
                    "fullName": item.canonical_name,
                    "displayName": item.display_name,
                    "club": item.club,
                    "position": str(item.position),
                }
                for item in self.players
            ],
            "aliases": [
                {"playerId": player_id, "aliases": sorted(values)}
                for player_id, values in sorted(self._aliases.items())
            ],
            "resolver_config": {
                "normalisationVersion": NAME_NORMALISATION_VERSION,
                "rapidfuzzVersion": rapidfuzz.__version__,
                "scorer": FUZZY_SCORER,
                "minimumScore": MIN_FUZZY_SCORE,
                "minimumMargin": MIN_FUZZY_MARGIN,
                "minimumReferenceLength": MIN_FUZZY_REFERENCE_LENGTH,
            },
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return sha256(encoded.encode("utf-8")).hexdigest()


class PlayerCatalogueProvider(Protocol):
    def get_current_catalogue(self, requested_season: str) -> PlayerCatalogue: ...


class LiveFplPlayerCatalogueProvider:
    def __init__(
        self,
        bootstrap_loader: Callable[[], Mapping[str, Any]],
        *,
        aliases: AliasConfiguration | None = None,
    ) -> None:
        self._bootstrap_loader = bootstrap_loader
        self._aliases = aliases

    def get_current_catalogue(self, requested_season: str) -> PlayerCatalogue:
        try:
            payload = self._bootstrap_loader()
        except CatalogueError:
            raise
        except Exception as exc:
            raise CatalogueUnavailable("bootstrap_static_unavailable") from exc
        season = _season_from_bootstrap(payload)
        if season is None:
            raise CatalogueUnavailable("catalogue_season_unavailable")
        if season != requested_season:
            raise CatalogueSeasonMismatch(
                f"requested {requested_season}, available {season}"
            )
        return catalogue_from_bootstrap(
            payload, season=season, aliases=self._aliases
        )


def _season_from_bootstrap(payload: Mapping[str, Any]) -> str | None:
    events = payload.get("events")
    if not isinstance(events, list):
        return None
    deadlines = [
        event.get("deadline_time")
        for event in events
        if isinstance(event, Mapping) and isinstance(event.get("deadline_time"), str)
    ]
    if not deadlines:
        return None
    try:
        year = int(min(deadlines)[:4])
    except (TypeError, ValueError):
        return None
    return f"{year:04d}-{(year + 1) % 100:02d}"


def catalogue_from_bootstrap(
    payload: Mapping[str, Any],
    *,
    season: str,
    aliases: AliasConfiguration | None = None,
) -> PlayerCatalogue:
    element_types = payload.get("element_types")
    teams = payload.get("teams")
    elements = payload.get("elements")
    if not all(isinstance(value, list) for value in (element_types, teams, elements)):
        raise CatalogueUnavailable("invalid_bootstrap_static")
    type_names = {
        item.get("id"): item.get("singular_name_short")
        for item in element_types
        if isinstance(item, Mapping)
    }
    clubs = {
        item.get("id"): item.get("name")
        for item in teams
        if isinstance(item, Mapping)
    }
    players: list[CataloguePlayer] = []
    for raw in elements:
        if not isinstance(raw, Mapping):
            raise CatalogueUnavailable("invalid_bootstrap_player")
        fpl_type = type_names.get(raw.get("element_type"))
        try:
            position = FPL_POSITION_TO_DOMAIN[str(fpl_type)]
        except KeyError as exc:
            raise UnknownFplPositionType(str(fpl_type)) from exc
        player_id = raw.get("id")
        if isinstance(player_id, bool) or not isinstance(player_id, int):
            raise CatalogueUnavailable("invalid_bootstrap_player_id")
        first = str(raw.get("first_name") or "").strip()
        second = str(raw.get("second_name") or "").strip()
        full_name = " ".join(part for part in (first, second) if part)
        display_name = str(raw.get("web_name") or full_name).strip()
        if not full_name:
            full_name = display_name
        cost = raw.get("now_cost")
        price = cost / 10 if isinstance(cost, int) else None
        players.append(
            CataloguePlayer(
                player_id,
                full_name,
                position,
                club=str(clubs.get(raw.get("team")) or "") or None,
                price=price,
                display_name=display_name,
            )
        )
    return PlayerCatalogue(
        players, season=season, aliases=aliases, source="fpl_bootstrap_static"
    )


__all__ = [
    "AliasConfiguration",
    "CatalogueError",
    "CataloguePlayer",
    "CatalogueSeasonMismatch",
    "CatalogueUnavailable",
    "FPL_POSITION_TO_DOMAIN",
    "FUZZY_SCORER",
    "InvalidAliasConfiguration",
    "LiveFplPlayerCatalogueProvider",
    "MIN_FUZZY_MARGIN",
    "MIN_FUZZY_REFERENCE_LENGTH",
    "MIN_FUZZY_SCORE",
    "PlayerCatalogue",
    "PlayerCatalogueProvider",
    "Position",
    "UnknownFplPositionType",
    "catalogue_from_bootstrap",
    "load_alias_configuration",
    "normalise_player_name",
]
