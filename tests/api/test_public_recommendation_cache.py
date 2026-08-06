from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from src.adapters.fpl import CurrentGameweek
from src.app.core.config import Settings
from src.app.core.dependencies import (
    get_app_settings,
    get_current_gameweek_service,
    get_public_recommendation_cache,
    get_report_service,
)
from src.app.core.public_recommendation_cache import (
    PublicRecommendationCache,
    cache_key,
    cache_metrics,
    cache_policy,
)
from src.app.domain.reports.service import (
    GameweekReportNotFoundError,
    ReportBundle,
)
from src.app.main import create_app
from src.schemas.final_report import FinalGameweekReport


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.fail_reads = False
        self.fail_writes = False
        self.deleted: list[str] = []

    def get(self, key: str) -> bytes | None:
        if self.fail_reads:
            raise TimeoutError("redis unavailable")
        return self.values.get(key)

    def set(self, key: str, value: bytes, *, ex: int) -> bool:
        if self.fail_writes:
            raise TimeoutError("redis unavailable")
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def delete(self, *keys: str) -> int:
        self.deleted.extend(keys)
        deleted = 0
        for key in keys:
            deleted += int(self.values.pop(key, None) is not None)
        return deleted


def _report(season: str, gameweek: int, overview: str) -> FinalGameweekReport:
    return FinalGameweekReport(
        season=season,
        gameweek=gameweek,
        overview=overview,
        conclusion="Conclusion",
    )


class VersionedReportService:
    def __init__(self) -> None:
        self.canonical: dict[tuple[str, int], str] = {}
        self.reports: dict[str, ReportBundle] = {}
        self.metadata_queries = 0
        self.payload_queries = 0

    def publish(
        self, season: str, gameweek: int, run_id: str, overview: str
    ) -> None:
        self.canonical[(season, gameweek)] = run_id
        self.reports[run_id] = ReportBundle(
            run_id=run_id,
            final_report=_report(season, gameweek, overview),
            aggregate_report=None,
            updated_at=datetime(2026, 8, 6, tzinfo=timezone.utc).timestamp(),
        )

    def get_public_recommendation_metadata(
        self, season: str, gameweek: int
    ) -> object:
        self.metadata_queries += 1
        try:
            run_id = self.canonical[(season, gameweek)]
        except KeyError as exc:
            raise GameweekReportNotFoundError(season, gameweek) from exc
        return SimpleNamespace(run_id=run_id)

    def get_public_recommendation_version(
        self, season: str, gameweek: int, run_id: str
    ) -> ReportBundle:
        self.payload_queries += 1
        if self.canonical.get((season, gameweek)) != run_id:
            raise GameweekReportNotFoundError(season, gameweek)
        return self.reports[run_id]


class StubCurrentGameweek:
    def get_upcoming_gameweek(self) -> CurrentGameweek:
        return CurrentGameweek(
            gameweek=32,
            deadline="2026-08-15T10:00:00Z",
            season="2025-26",
        )


def _client(
    service: VersionedReportService, redis: FakeRedis
) -> tuple[TestClient, PublicRecommendationCache, Settings]:
    cache = PublicRecommendationCache(redis)
    settings = Settings(
        PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS=30,
        PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS=600,
        PUBLIC_RECOMMENDATION_CURRENT_SWR_SECONDS=5,
        PUBLIC_RECOMMENDATION_HISTORICAL_SWR_SECONDS=60,
    )
    app = create_app()
    app.dependency_overrides[get_report_service] = lambda: service
    app.dependency_overrides[get_current_gameweek_service] = StubCurrentGameweek
    app.dependency_overrides[get_public_recommendation_cache] = lambda: cache
    app.dependency_overrides[get_app_settings] = lambda: settings
    return TestClient(app), cache, settings


def test_historical_miss_then_hit_avoids_full_postgres_payload_query() -> None:
    service = VersionedReportService()
    service.publish("2025-26", 30, "historical-run", "Historical")
    redis = FakeRedis()
    client, _, settings = _client(service, redis)

    first = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )
    second = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )

    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    assert service.metadata_queries == 2
    assert service.payload_queries == 1
    key = cache_key("2025-26", 30, "historical-run")
    assert redis.ttls[key] == settings.PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS
    assert "max-age=600" in second.headers["cache-control"]


def test_current_gameweek_uses_shorter_ttl_and_keys_are_fully_scoped() -> None:
    service = VersionedReportService()
    service.publish("2025-26", 32, "shared-id", "Current")
    service.publish("2024-25", 32, "other-run", "Past season")
    redis = FakeRedis()
    client, _, settings = _client(service, redis)

    for season in ("2025-26", "2024-25"):
        assert client.get(
            "/api/recommendations",
            params={"season": season, "gameweek": 32},
        ).status_code == 200

    current_key = cache_key("2025-26", 32, "shared-id")
    historical_key = cache_key("2024-25", 32, "other-run")
    assert set(redis.values) == {current_key, historical_key}
    assert redis.ttls[current_key] == settings.PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS
    assert (
        redis.ttls[historical_key]
        == settings.PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS
    )


def test_cache_policy_explicitly_handles_current_recent_historical_and_unknown() -> None:
    settings = Settings(
        PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS=30,
        PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS=600,
        PUBLIC_RECOMMENDATION_CURRENT_SWR_SECONDS=5,
        PUBLIC_RECOMMENDATION_HISTORICAL_SWR_SECONDS=60,
        PUBLIC_RECOMMENDATION_RECENT_GAMEWEEKS=1,
    )
    current = CurrentGameweek(
        gameweek=32,
        deadline="2026-08-15T10:00:00Z",
        season="2025-26",
    )

    current_policy = cache_policy(
        settings, season="2025-26", gameweek=32, current=current
    )
    recent_policy = cache_policy(
        settings, season="2025-26", gameweek=31, current=current
    )
    historical_policy = cache_policy(
        settings, season="2025-26", gameweek=30, current=current
    )
    past_season_policy = cache_policy(
        settings, season="2024-25", gameweek=38, current=current
    )
    unknown_policy = cache_policy(
        settings, season="2025-26", gameweek=1, current=None
    )

    assert current_policy.historical is False
    assert recent_policy.historical is False
    assert historical_policy.historical is True
    assert past_season_policy.historical is True
    assert unknown_policy.historical is False
    assert historical_policy.ttl_seconds > current_policy.ttl_seconds
    assert unknown_policy.ttl_seconds == current_policy.ttl_seconds


def test_cache_settings_reject_a_non_longer_historical_ttl() -> None:
    with pytest.raises(
        ValueError,
        match="PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS must be greater",
    ):
        Settings(
            PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS=300,
            PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS=300,
        )


def test_replacement_publication_cannot_retrieve_superseded_cached_response() -> None:
    service = VersionedReportService()
    service.publish("2025-26", 30, "run-a", "Old publication")
    redis = FakeRedis()
    client, cache, _ = _client(service, redis)

    old = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )
    service.publish("2025-26", 30, "run-b", "Replacement publication")
    cache.invalidate_versions(season="2025-26", gameweek=30, run_ids=["run-a"])
    replacement = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )

    assert old.json()["report"]["overview"] == "Old publication"
    assert replacement.json()["report"]["overview"] == "Replacement publication"
    assert cache_key("2025-26", 30, "run-a") in redis.deleted
    assert cache_key("2025-26", 30, "run-b") in redis.values


def test_redis_failure_and_corrupt_values_fall_back_and_repopulate(
    caplog,
) -> None:
    service = VersionedReportService()
    service.publish("2025-26", 30, "run-a", "Database response")
    redis = FakeRedis()
    client, _, _ = _client(service, redis)
    key = cache_key("2025-26", 30, "run-a")

    redis.fail_reads = True
    with caplog.at_level(logging.WARNING):
        failed_read = client.get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 30},
        )
    assert failed_read.status_code == 200
    assert failed_read.json()["report"]["overview"] == "Database response"
    assert "public_recommendation_cache_read_failed" in caplog.text

    redis.fail_reads = False
    redis.values[key] = b'{"season":"wrong"}'
    rebuilt = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )
    assert rebuilt.status_code == 200
    assert json.loads(redis.values[key])["report"]["overview"] == "Database response"
    assert service.payload_queries == 2


def test_redis_write_failure_does_not_change_the_public_response(caplog) -> None:
    cache_metrics.reset_for_tests()
    service = VersionedReportService()
    service.publish("2025-26", 30, "run-a", "Database response")
    redis = FakeRedis()
    redis.fail_writes = True
    client, _, _ = _client(service, redis)

    with caplog.at_level(logging.WARNING):
        response = client.get(
            "/api/recommendations",
            params={"season": "2025-26", "gameweek": 30},
        )

    assert response.status_code == 200
    assert response.json()["report"]["overview"] == "Database response"
    assert redis.values == {}
    assert cache_metrics.snapshot()["write_failure"] == 1
    assert "public_recommendation_cache_write_failed" in caplog.text


def test_etag_conditional_request_and_cached_contract_are_public_only() -> None:
    service = VersionedReportService()
    service.publish("2025-26", 30, "private-internal-run-id", "Public response")
    redis = FakeRedis()
    client, _, _ = _client(service, redis)

    response = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
    )
    conditional = client.get(
        "/api/recommendations",
        params={"season": "2025-26", "gameweek": 30},
        headers={"If-None-Match": response.headers["etag"]},
    )

    assert response.status_code == 200
    assert response.headers["etag"].startswith('"publication-')
    assert conditional.status_code == 304
    assert conditional.content == b""
    cached = redis.values[cache_key("2025-26", 30, "private-internal-run-id")]
    assert json.loads(cached) == response.json()
    assert b"private-internal-run-id" not in cached
    assert b"access_token" not in cached
    assert service.payload_queries == 1


def test_hit_miss_and_failure_metrics_are_emitted() -> None:
    cache_metrics.reset_for_tests()
    service = VersionedReportService()
    service.publish("2025-26", 30, "run-a", "Response")
    redis = FakeRedis()
    client, _, _ = _client(service, redis)
    params = {"season": "2025-26", "gameweek": 30}

    assert client.get("/api/recommendations", params=params).status_code == 200
    assert client.get("/api/recommendations", params=params).status_code == 200
    redis.fail_reads = True
    assert client.get("/api/recommendations", params=params).status_code == 200

    metrics = cache_metrics.snapshot()
    assert metrics["miss"] == 1
    assert metrics["hit"] == 1
    assert metrics["read_failure"] == 1
