from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.core.config import get_settings


def normalize_database_url(url: str) -> str:
    """Accept common provider URLs while using psycopg 3 explicitly."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().DATABASE_URL.strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required when TRANSCRIPT_STORE=postgres")
    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
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
