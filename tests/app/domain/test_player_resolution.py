from __future__ import annotations

import json

import pytest

from src.app.domain.reports.player_catalogue import (
    AliasConfiguration,
    CataloguePlayer,
    CatalogueSeasonMismatch,
    InvalidAliasConfiguration,
    LiveFplPlayerCatalogueProvider,
    PersistedPlayerCatalogueProvider,
    PlayerCatalogue,
    SeasonAwarePlayerCatalogueProvider,
    UnknownFplPositionType,
    catalogue_from_bootstrap,
    load_catalogue_snapshot,
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


def test_persisted_snapshot_loads_metadata_and_rejects_season_mismatch(
    tmp_path,
) -> None:
    snapshot = {
        "schemaVersion": 1,
        "snapshotId": "2025-26:test",
        "season": "2025-26",
        "source": "archived_fpl_bootstrap",
        "retrievedAt": "2026-05-25T00:00:00Z",
        "players": [
            {
                "playerId": 1,
                "canonicalName": "Bukayo Saka",
                "displayName": "Saka",
                "team": "Arsenal",
                "position": "MID",
                "price": 10.0,
                "aliases": ["Starboy"],
            }
        ],
    }
    path = tmp_path / "2025-26.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    catalogue = load_catalogue_snapshot(path)
    provider = PersistedPlayerCatalogueProvider(tmp_path)

    assert catalogue.season == "2025-26"
    assert catalogue.snapshot_id == "2025-26:test"
    assert catalogue.resolve("Starboy").official_player_id == 1  # type: ignore[union-attr]
    assert provider.get_catalogue("2025-26").source == "archived_fpl_bootstrap"

    snapshot["season"] = "2024-25"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(CatalogueSeasonMismatch):
        provider.get_catalogue("2025-26")


def test_season_aware_provider_never_falls_back_to_live_for_history() -> None:
    calls: list[tuple[str, str]] = []

    class Provider:
        def __init__(self, label: str) -> None:
            self.label = label

        def get_catalogue(self, season: str) -> PlayerCatalogue:
            calls.append((self.label, season))
            return PlayerCatalogue(_players(), season=season, source=self.label)

    provider = SeasonAwarePlayerCatalogueProvider(
        Provider("live"),
        Provider("snapshot"),
        current_season="2026-27",
    )

    assert provider.get_catalogue("2025-26").source == "snapshot"
    assert provider.get_catalogue("2026-27").source == "live"
    assert calls == [("snapshot", "2025-26"), ("live", "2026-27")]
