from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from src.app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from src.adapters.fpl import FplApiClient
    from src.app.domain.reports.player_catalogue import PlayerCatalogueProvider
    from src.app.domain.reports.service import ReportService
    from src.app.core.public_recommendation_cache import PublicRecommendationCache


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_report_service() -> ReportService:
    from src.app.domain.reports.service import ReportService

    return ReportService()


@lru_cache
def get_current_gameweek_service() -> FplApiClient:
    from src.adapters.fpl import get_fpl_api_client

    return get_fpl_api_client()


@lru_cache
def get_public_recommendation_cache() -> PublicRecommendationCache:
    from redis import Redis

    from src.app.core.public_recommendation_cache import PublicRecommendationCache

    settings = get_app_settings()
    if not settings.REDIS_URL.strip():
        return PublicRecommendationCache()
    client = Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=(
            settings.PUBLIC_RECOMMENDATION_REDIS_TIMEOUT_SECONDS
        ),
        socket_timeout=settings.PUBLIC_RECOMMENDATION_REDIS_TIMEOUT_SECONDS,
        retry_on_timeout=False,
    )
    return PublicRecommendationCache(client)


@lru_cache
def get_current_player_catalogue_provider() -> PlayerCatalogueProvider:
    from src.adapters.fpl import get_player_catalogue_provider

    return get_player_catalogue_provider()
