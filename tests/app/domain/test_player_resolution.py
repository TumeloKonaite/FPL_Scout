from __future__ import annotations

import pytest

from src.app.domain.reports.player_catalogue import (
    AliasConfiguration,
    CataloguePlayer,
    CatalogueSeasonMismatch,
    InvalidAliasConfiguration,
    LiveFplPlayerCatalogueProvider,
    PlayerCatalogue,
    UnknownFplPositionType,
    catalogue_from_bootstrap,
)
from src.app.domain.reports.player_resolution import PlayerResolver
from src.schemas.player_resolution import ExtractedPlayerReference, ResolutionSource


def _players() -> list[CataloguePlayer]:
    return [
        CataloguePlayer(1, "Bukayo Saka", "MID", "Arsenal", display_name="Saka"),
        CataloguePlayer(2, "Mohamed Salah", "MID", "Liverpool", display_name="Salah"),
        CataloguePlayer(3, "William Saliba", "DEF", "Arsenal", display_name="Saliba"),
    ]


def _source() -> ResolutionSource:
    return ResolutionSource(
        expertId="expert-1", videoId="video-1", squadRole="starter"
    )


def test_exact_id_conflict_matrix_and_unknown_id_fail_closed() -> None:
    resolver = PlayerResolver(PlayerCatalogue(_players(), season="2025-26"))

    same = resolver.resolve(
        ExtractedPlayerReference(name="Saka", playerId=1), source=_source()
    )
    typo = resolver.resolve(
        ExtractedPlayerReference(name="unrelated typo", playerId=1),
        source=_source(),
    )
    conflict = resolver.resolve(
        ExtractedPlayerReference(name="Salah", playerId=1), source=_source()
    )
    unknown = resolver.resolve(
        ExtractedPlayerReference(name="Saka", playerId=999), source=_source()
    )

    assert same.player is not None and same.event.method == "player_id"
    assert typo.player is not None
    assert typo.event.warnings == ["unverified_name_for_player_id"]
    assert conflict.player is None
    assert conflict.event.reason == "player_id_name_conflict"
    assert conflict.event.canonicalPlayerId is None
    assert conflict.event.conflictingPlayerId == 2
    assert unknown.player is None
    assert unknown.event.reason == "unknown_player_id"


def test_fuzzy_resolution_is_diagnostic_and_position_is_only_a_warning() -> None:
    resolver = PlayerResolver(PlayerCatalogue(_players(), season="2025-26"))

    result = resolver.resolve(
        ExtractedPlayerReference(name="Bukayo Sakaa", positionHint="FWD"),
        source=_source(),
    )

    assert result.player is not None
    assert result.player.official_player_id == 1
    assert result.event.method == "fuzzy"
    assert result.event.match is not None
    assert result.event.match.algorithm == "rapidfuzz.fuzz.WRatio"
    assert "position_mismatch" in result.event.warnings


def test_alias_configuration_is_atomic_and_changes_fingerprint() -> None:
    base = PlayerCatalogue(_players(), season="2025-26")
    with_alias = PlayerCatalogue(
        _players(),
        season="2025-26",
        aliases=AliasConfiguration("2025-26", {1: ["Starboy"]}),
    )
    assert with_alias.resolve("Starboy").official_player_id == 1  # type: ignore[union-attr]
    assert base.fingerprint != with_alias.fingerprint

    with pytest.raises(InvalidAliasConfiguration):
        PlayerCatalogue(
            _players(),
            season="2025-26",
            aliases=AliasConfiguration("2025-26", {999: ["Ghost"]}),
        )
    with pytest.raises(InvalidAliasConfiguration):
        PlayerCatalogue(
            _players(),
            season="2025-26",
            aliases=AliasConfiguration("2025-26", {1: ["Salah"]}),
        )
    with pytest.raises(InvalidAliasConfiguration):
        PlayerCatalogue(
            _players(),
            season="2025-26",
            aliases=AliasConfiguration("2024-25", {1: ["Starboy"]}),
        )


def test_live_provider_serves_only_bootstrap_season_and_maps_positions() -> None:
    payload = {
        "events": [{"deadline_time": "2025-08-15T18:30:00Z"}],
        "element_types": [
            {"id": 1, "singular_name_short": "GKP"},
            {"id": 3, "singular_name_short": "MID"},
        ],
        "teams": [{"id": 1, "name": "Arsenal"}],
        "elements": [
            {
                "id": 1,
                "first_name": "Bukayo",
                "second_name": "Saka",
                "web_name": "Saka",
                "element_type": 3,
                "team": 1,
                "now_cost": 100,
            }
        ],
    }
    provider = LiveFplPlayerCatalogueProvider(lambda: payload)
    catalogue = provider.get_current_catalogue("2025-26")

    assert catalogue.by_id(1).position == "MID"  # type: ignore[union-attr]
    with pytest.raises(CatalogueSeasonMismatch):
        provider.get_current_catalogue("2024-25")

    payload["element_types"][1]["singular_name_short"] = "UNKNOWN"
    with pytest.raises(UnknownFplPositionType):
        catalogue_from_bootstrap(payload, season="2025-26")
