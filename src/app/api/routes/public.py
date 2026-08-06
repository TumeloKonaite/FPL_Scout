from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import AfterValidator

from src.adapters.fpl import FplApiClient, FplApiError
from src.app.api.schemas.public import (
    AvailableGameweeksResponse,
    CurrentGameweekResponse,
    GameweekReportSummary,
    LatestRecommendationsResponse,
    PublicRecommendationResponse,
    SeasonGameweekIndex,
)
from src.app.core.config import Settings
from src.app.core.dependencies import (
    get_app_settings,
    get_current_gameweek_service,
    get_public_recommendation_cache,
    get_report_service,
)
from src.app.core.public_recommendation_cache import (
    CachePolicy,
    PublicRecommendationCache,
    cache_key,
    cache_policy,
)
from src.app.domain.reports.service import (
    EmptyReportDirectoryError,
    GameweekReportNotFoundError,
    InvalidReportFileError,
    ReportBundle,
    ReportDirectoryNotFoundError,
    ReportService,
)
from src.schemas.report_identity import validate_season
from src.app.core.public_recommendation_timing import current_timing, measure

router = APIRouter(prefix="/api", tags=["Public recommendations"])
cache_logger = logging.getLogger("src.app.cache.public_recommendations")
UNAVAILABLE_DETAIL = "The latest gameweek analysis is temporarily unavailable."
SeasonQuery = Annotated[str, AfterValidator(validate_season), Query()]


def _load_latest(
    service: ReportService,
    season: str | None = None,
    gameweek: int | None = None,
) -> ReportBundle:
    try:
        return (
            service.get_public_recommendation(season, gameweek)
            if season and gameweek
            else service.get_latest_public_report()
        )
    except (
        EmptyReportDirectoryError,
        GameweekReportNotFoundError,
        ReportDirectoryNotFoundError,
    ) as exc:
        raise HTTPException(status_code=404, detail=UNAVAILABLE_DETAIL) from exc
    except InvalidReportFileError as exc:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc


def _last_updated(report: ReportBundle) -> str | None:
    updated_at = getattr(report, "updated_at", None)
    if updated_at is not None:
        return datetime.fromtimestamp(updated_at, tz=UTC).isoformat()
    public_value = getattr(report.final_report, "lastUpdated", None)
    if public_value:
        return str(public_value)
    return None


def _report_payload(report: ReportBundle) -> dict[str, Any]:
    return report.final_report.model_dump()


def _publication_etag(run_id: str) -> str:
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]
    return f'"publication-{digest}"'


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    if not if_none_match:
        return False
    for candidate in if_none_match.split(","):
        value = candidate.strip()
        if value == "*":
            return True
        if value.startswith("W/"):
            value = value[2:].strip()
        if value == etag:
            return True
    return False


def _cache_headers(run_id: str, policy: CachePolicy) -> dict[str, str]:
    return {
        "Cache-Control": policy.cache_control,
        "ETag": _publication_etag(run_id),
    }


def _serialize_public_response(response_model: PublicRecommendationResponse) -> bytes:
    return json.dumps(
        response_model.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _record_cache_lookup(
    *,
    season: str,
    gameweek: int,
    run_id: str,
    status: str,
    read_ms: float,
    database_fallback: bool,
    policy: CachePolicy,
    population_ms: float | None = None,
) -> None:
    cache_logger.info(
        "public recommendation cache lookup completed",
        extra={
            "cache_event": {
                "event": "public_recommendation_cache_lookup_completed",
                "season": season,
                "gameweek": gameweek,
                "run_id": run_id,
                "cache_status": status,
                "cache_read_ms": read_ms,
                "cache_population_ms": population_ms,
                "database_fallback": database_fallback,
                "historical": policy.historical,
                "ttl_seconds": policy.ttl_seconds,
            }
        },
    )


@router.get("/recommendations/latest", response_model=LatestRecommendationsResponse)
def get_latest_recommendations(
    service: ReportService = Depends(get_report_service),
    fpl: FplApiClient = Depends(get_current_gameweek_service),
) -> LatestRecommendationsResponse:
    current = None
    try:
        current = fpl.get_upcoming_gameweek()
    except FplApiError:
        pass
    report = _load_latest(
        service,
        current.season if current is not None else None,
        current.gameweek if current is not None and current.season else None,
    )
    return LatestRecommendationsResponse(
        season=report.final_report.season,
        gameweek=report.final_report.gameweek,
        last_updated_at=_last_updated(report),
        report=_report_payload(report),
    )


@router.get("/recommendations/gameweeks", response_model=AvailableGameweeksResponse)
def list_available_gameweeks(
    service: ReportService = Depends(get_report_service),
) -> AvailableGameweeksResponse:
    try:
        seasons = service.list_available_gameweeks()
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        seasons = []
    return AvailableGameweeksResponse(
        seasons=[
            SeasonGameweekIndex(
                season=season.season,
                gameweeks=[
                    GameweekReportSummary(
                        gameweek=gameweek.gameweek,
                        last_updated_at=gameweek.last_updated_at,
                        has_suggested_team=gameweek.has_suggested_team,
                    )
                    for gameweek in season.gameweeks
                ],
            )
            for season in seasons
        ]
    )


@router.get("/recommendations", response_model=PublicRecommendationResponse)
def get_recommendations(
    season: SeasonQuery,
    gameweek: Annotated[int, Query(ge=1, le=38)],
    request: Request,
    service: ReportService = Depends(get_report_service),
    fpl: FplApiClient = Depends(get_current_gameweek_service),
    cache: PublicRecommendationCache = Depends(get_public_recommendation_cache),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    timing = current_timing()
    if timing is not None:
        timing.season = season
        timing.gameweek = gameweek

    current = None
    if cache.enabled:
        try:
            current = fpl.get_upcoming_gameweek()
        except FplApiError:
            # Unknown state deliberately selects the short, mutable policy.
            pass
    policy = cache_policy(
        settings,
        season=season,
        gameweek=gameweek,
        current=current,
    )
    if timing is not None:
        timing.historical = policy.historical
        timing.ttl_seconds = policy.ttl_seconds

    supports_versioned_lookup = all(
        hasattr(service, name)
        for name in (
            "get_public_recommendation_metadata",
            "get_public_recommendation_version",
        )
    )
    if cache.enabled and supports_versioned_lookup:
        return _get_versioned_recommendation(
            season=season,
            gameweek=gameweek,
            request=request,
            service=service,
            cache=cache,
            policy=policy,
        )

    # Compatibility and cache-disabled path: preserve the original single-query
    # behavior and response contract.
    try:
        report = service.get_public_recommendation(season, gameweek)
    except GameweekReportNotFoundError:
        if timing is not None and timing.failure_stage is None:
            timing.mark_failure("recommendation_lookup", category="report_not_found")
        return _not_found_response(season, gameweek)
    except (EmptyReportDirectoryError, ReportDirectoryNotFoundError):
        if timing is not None:
            timing.mark_failure("recommendation_lookup", category="report_not_found")
        return _not_found_response(season, gameweek)
    except InvalidReportFileError as exc:
        if timing is not None:
            timing.mark_failure(
                "final_report_validation", exc, category="invalid_stored_report"
            )
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc
    if timing is not None:
        timing.run_id = report.run_id
        timing.cache_status = "not_configured"
    headers = _cache_headers(report.run_id, policy)
    if _etag_matches(request.headers.get("if-none-match"), headers["ETag"]):
        return Response(status_code=304, headers=headers)
    payload = _build_public_response_payload(report)
    return Response(content=payload, media_type="application/json", headers=headers)


def _get_versioned_recommendation(
    *,
    season: str,
    gameweek: int,
    request: Request,
    service: ReportService,
    cache: PublicRecommendationCache,
    policy: CachePolicy,
) -> Response:
    timing = current_timing()
    for attempt in range(2):
        try:
            metadata = service.get_public_recommendation_metadata(season, gameweek)
        except GameweekReportNotFoundError:
            if timing is not None and timing.failure_stage is None:
                timing.mark_failure(
                    "recommendation_lookup", category="report_not_found"
                )
            return _not_found_response(season, gameweek)
        run_id = metadata.run_id
        if timing is not None:
            timing.run_id = run_id
        headers = _cache_headers(run_id, policy)
        if _etag_matches(request.headers.get("if-none-match"), headers["ETag"]):
            if timing is not None:
                timing.cache_status = "not_checked"
            return Response(status_code=304, headers=headers)

        key = cache_key(season, gameweek, run_id)
        cached = cache.read(
            key,
            season=season,
            gameweek=gameweek,
            run_id=run_id,
        )
        if timing is not None:
            timing.cache_status = cached.status
            timing.cache_read_ms = cached.duration_ms
        if cached.payload is not None:
            _record_cache_lookup(
                season=season,
                gameweek=gameweek,
                run_id=run_id,
                status="hit",
                read_ms=cached.duration_ms,
                database_fallback=False,
                policy=policy,
            )
            return Response(
                content=cached.payload,
                media_type="application/json",
                headers=headers,
            )

        if timing is not None:
            timing.database_fallback = True
        try:
            report = service.get_public_recommendation_version(
                season, gameweek, run_id
            )
        except GameweekReportNotFoundError:
            # A replacement may have committed between metadata resolution and
            # payload loading. Re-resolve once rather than serving the old run.
            if attempt == 0:
                continue
            if timing is not None and timing.failure_stage is None:
                timing.mark_failure(
                    "recommendation_lookup", category="report_not_found"
                )
            return _not_found_response(season, gameweek)

        payload = _build_public_response_payload(report)
        _, population_ms = cache.write(
            key,
            payload,
            ttl_seconds=policy.ttl_seconds,
            season=season,
            gameweek=gameweek,
            run_id=run_id,
        )
        if timing is not None:
            timing.cache_population_ms = population_ms
        _record_cache_lookup(
            season=season,
            gameweek=gameweek,
            run_id=run_id,
            status=cached.status,
            read_ms=cached.duration_ms,
            database_fallback=True,
            policy=policy,
            population_ms=population_ms,
        )
        return Response(content=payload, media_type="application/json", headers=headers)

    return _not_found_response(season, gameweek)


def _build_public_response_payload(report: ReportBundle) -> bytes:
    with measure("response_model_ms", "response_model_construction"):
        response_model = PublicRecommendationResponse(
            season=report.final_report.season,
            gameweek=report.final_report.gameweek,
            last_updated_at=_last_updated(report),
            report=_report_payload(report),
        )
    with measure("serialization_ms", "response_serialization"):
        return _serialize_public_response(response_model)


def _not_found_response(season: str, gameweek: int) -> JSONResponse:
    content = {
        "error": {
            "code": "REPORT_NOT_FOUND",
            "message": (
                "No completed report is available for season "
                f"{season}, gameweek {gameweek}."
            ),
            "details": {"season": season, "gameweek": gameweek},
        }
    }
    with measure("serialization_ms", "response_serialization"):
        return JSONResponse(status_code=404, content=content)


@router.get("/gameweek/current", response_model=CurrentGameweekResponse)
def get_current_gameweek(
    service: ReportService = Depends(get_report_service),
    fpl: FplApiClient = Depends(get_current_gameweek_service),
) -> CurrentGameweekResponse:
    try:
        current = fpl.get_upcoming_gameweek()
    except FplApiError as exc:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc
    if current is None:
        return CurrentGameweekResponse(recommendations_available=False)

    try:
        report = _load_latest(service, current.season, current.gameweek)
    except HTTPException as exc:
        if exc.status_code == 404:
            return CurrentGameweekResponse(
                gameweek=current.gameweek,
                deadline=current.deadline,
                recommendations_available=False,
            )
        raise
    report_is_current = report.final_report.gameweek == current.gameweek and (
        current.season is None or report.final_report.season == current.season
    )
    return CurrentGameweekResponse(
        gameweek=current.gameweek,
        deadline=current.deadline,
        last_updated_at=_last_updated(report),
        recommendations_available=report_is_current,
    )
