from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import logging
from threading import Lock
from time import perf_counter
from typing import Any, Protocol

from src.adapters.fpl import CurrentGameweek
from src.app.core.config import Settings


logger = logging.getLogger("src.app.cache.public_recommendations")
CACHE_KEY_PREFIX = "public-recommendations"


class RedisClient(Protocol):
    def get(self, key: str) -> bytes | str | None: ...

    def set(self, key: str, value: bytes, *, ex: int) -> object: ...

    def delete(self, *keys: str) -> int: ...


@dataclass(frozen=True, slots=True)
class CachePolicy:
    ttl_seconds: int
    stale_while_revalidate_seconds: int
    historical: bool

    @property
    def cache_control(self) -> str:
        return (
            f"public, max-age={self.ttl_seconds}, "
            f"stale-while-revalidate={self.stale_while_revalidate_seconds}"
        )


@dataclass(frozen=True, slots=True)
class CacheRead:
    status: str
    payload: bytes | None
    duration_ms: float


class PublicRecommendationCacheMetrics:
    """Small in-process counters for deployments without a metrics backend."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: Counter[str] = Counter()

    def increment(self, status: str) -> None:
        with self._lock:
            self._counts[status] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def reset_for_tests(self) -> None:
        with self._lock:
            self._counts.clear()


cache_metrics = PublicRecommendationCacheMetrics()


def cache_key(season: str, gameweek: int, run_id: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{season}:{gameweek}:{run_id}"


def cache_policy(
    settings: Settings,
    *,
    season: str,
    gameweek: int,
    current: CurrentGameweek | None,
) -> CachePolicy:
    # Unknown current-gameweek state deliberately receives the short policy.
    historical = bool(
        current is not None
        and current.season is not None
        and (
            season != current.season
            or gameweek
            < current.gameweek - settings.PUBLIC_RECOMMENDATION_RECENT_GAMEWEEKS
        )
    )
    if historical:
        return CachePolicy(
            ttl_seconds=settings.PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS,
            stale_while_revalidate_seconds=(
                settings.PUBLIC_RECOMMENDATION_HISTORICAL_SWR_SECONDS
            ),
            historical=True,
        )
    return CachePolicy(
        ttl_seconds=settings.PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS,
        stale_while_revalidate_seconds=(
            settings.PUBLIC_RECOMMENDATION_CURRENT_SWR_SECONDS
        ),
        historical=False,
    )


def _duration_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def _valid_public_payload(payload: object, *, season: str, gameweek: int) -> bool:
    if not isinstance(payload, dict):
        return False
    report = payload.get("report")
    return bool(
        payload.get("season") == season
        and payload.get("gameweek") == gameweek
        and payload.get("available") is True
        and isinstance(report, dict)
        and report.get("season") == season
        and report.get("gameweek") == gameweek
    )


class PublicRecommendationCache:
    """Cache only the serialized, already-validated public API response."""

    def __init__(self, client: RedisClient | None = None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def read(
        self, key: str, *, season: str, gameweek: int, run_id: str
    ) -> CacheRead:
        if self._client is None:
            return CacheRead("not_configured", None, 0.0)
        started_at = perf_counter()
        try:
            value = self._client.get(key)
        except Exception as exc:
            duration = _duration_ms(started_at)
            cache_metrics.increment("read_failure")
            self._log_failure(
                "public_recommendation_cache_read_failed",
                exc,
                season=season,
                gameweek=gameweek,
                run_id=run_id,
                cache_read_ms=duration,
            )
            return CacheRead("read_failure", None, duration)
        duration = _duration_ms(started_at)
        if value is None:
            cache_metrics.increment("miss")
            return CacheRead("miss", None, duration)
        raw = value.encode("utf-8") if isinstance(value, str) else value
        try:
            decoded: Any = json.loads(raw)
            if not _valid_public_payload(
                decoded, season=season, gameweek=gameweek
            ):
                raise ValueError("cached public response has an incompatible schema")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            cache_metrics.increment("corrupt")
            self._log_failure(
                "public_recommendation_cache_value_invalid",
                exc,
                season=season,
                gameweek=gameweek,
                run_id=run_id,
                cache_read_ms=duration,
            )
            self.invalidate_keys(
                [key], season=season, gameweek=gameweek, run_id=run_id
            )
            return CacheRead("corrupt", None, duration)
        cache_metrics.increment("hit")
        return CacheRead("hit", raw, duration)

    def write(
        self,
        key: str,
        payload: bytes,
        *,
        ttl_seconds: int,
        season: str,
        gameweek: int,
        run_id: str,
    ) -> tuple[bool, float]:
        if self._client is None:
            return False, 0.0
        started_at = perf_counter()
        try:
            self._client.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            duration = _duration_ms(started_at)
            cache_metrics.increment("write_failure")
            self._log_failure(
                "public_recommendation_cache_write_failed",
                exc,
                season=season,
                gameweek=gameweek,
                run_id=run_id,
                ttl_seconds=ttl_seconds,
                cache_population_ms=duration,
            )
            return False, duration
        duration = _duration_ms(started_at)
        cache_metrics.increment("write")
        return True, duration

    def invalidate_versions(
        self, *, season: str, gameweek: int, run_ids: list[str]
    ) -> None:
        self.invalidate_keys(
            [cache_key(season, gameweek, run_id) for run_id in run_ids],
            season=season,
            gameweek=gameweek,
            run_id=run_ids[-1] if run_ids else None,
        )

    def invalidate_keys(
        self,
        keys: list[str],
        *,
        season: str,
        gameweek: int,
        run_id: str | None,
    ) -> None:
        if self._client is None or not keys:
            return
        try:
            deleted = self._client.delete(*keys)
        except Exception as exc:
            cache_metrics.increment("invalidation_failure")
            self._log_failure(
                "public_recommendation_cache_invalidation_failed",
                exc,
                season=season,
                gameweek=gameweek,
                run_id=run_id,
            )
            return
        cache_metrics.increment("invalidation")
        logger.info(
            "public recommendation cache invalidated",
            extra={
                "cache_event": {
                    "event": "public_recommendation_cache_invalidated",
                    "season": season,
                    "gameweek": gameweek,
                    "run_id": run_id,
                    "deleted_keys": deleted,
                }
            },
        )

    @staticmethod
    def _log_failure(event: str, exc: Exception, **context: object) -> None:
        logger.warning(
            event,
            extra={
                "cache_event": {
                    "event": event,
                    **context,
                    "exception_type": type(exc).__name__,
                }
            },
        )
