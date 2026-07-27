from __future__ import annotations

from functools import lru_cache
import logging
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from src.app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def normalize_database_url(url: str) -> str:
    """Accept common provider URLs while using psycopg 3 explicitly."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def is_transaction_pooler(url: str, pool_mode: str = "auto") -> bool:
    """Identify Supavisor/PgBouncer transaction endpoints."""
    if pool_mode == "transaction":
        return True
    if pool_mode in {"direct", "session"}:
        return False
    parsed = make_url(normalize_database_url(url))
    return parsed.port == 6543


def database_engine_options(
    settings: Settings,
    *,
    migration: bool = False,
) -> dict[str, Any]:
    """Build bounded, psycopg-compatible connection options."""
    url = (
        (settings.DIRECT_DATABASE_URL or settings.DATABASE_URL)
        if migration
        else settings.DATABASE_URL
    )
    connect_args: dict[str, Any] = {
        "connect_timeout": settings.DATABASE_CONNECT_TIMEOUT_SECONDS,
    }
    if settings.ENVIRONMENT.casefold() == "production":
        connect_args["sslmode"] = "require"
    if is_transaction_pooler(url, settings.DATABASE_POOL_MODE if not migration else "auto"):
        # Transaction pooling cannot retain server-side prepared statements.
        connect_args["prepare_threshold"] = None

    options: dict[str, Any] = {"connect_args": connect_args}
    if not migration:
        options.update(
            pool_pre_ping=True,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
            pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
        )
    return options


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    database_url = settings.DATABASE_URL.strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return create_engine(
        normalize_database_url(database_url),
        **database_engine_options(settings),
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def dispose_engine() -> None:
    """Close pooled connections at a worker invocation boundary."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def database_is_ready(engine: Engine | None = None) -> bool:
    """Return whether the configured database accepts a lightweight query."""
    try:
        with (engine or get_engine()).connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    except Exception as exc:
        # Deliberately omit exception text: drivers may include connection details.
        logger.warning("database readiness check failed (%s)", type(exc).__name__)
        return False


def require_database_ready(engine: Engine | None = None) -> None:
    if not database_is_ready(engine):
        raise RuntimeError("Production database is unavailable")
