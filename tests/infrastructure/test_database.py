from __future__ import annotations

from src.app.core.config import Settings
from src.app.infrastructure.database import (
    database_engine_options,
    database_is_ready,
    is_transaction_pooler,
    normalize_database_url,
)


def _production_settings(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": (
            "postgres://postgres.project:secret@aws-0.pooler.supabase.com:6543/postgres"
        ),
        "DIRECT_DATABASE_URL": (
            "postgresql://postgres:secret@db.project.supabase.co:5432/postgres"
        ),
        "DATABASE_POOL_MODE": "transaction",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_normalizes_supabase_style_postgres_urls() -> None:
    assert normalize_database_url(
        "postgres://postgres.project:secret@pooler.supabase.com:6543/postgres"
    ) == (
        "postgresql+psycopg://"
        "postgres.project:secret@pooler.supabase.com:6543/postgres"
    )
    assert normalize_database_url(
        "postgresql://postgres:secret@db.project.supabase.co:5432/postgres"
    ) == (
        "postgresql+psycopg://"
        "postgres:secret@db.project.supabase.co:5432/postgres"
    )


def test_transaction_pooler_is_detected_from_mode_or_port() -> None:
    url = "postgresql://postgres.project:secret@pooler.supabase.com:6543/postgres"
    assert is_transaction_pooler(url)
    assert is_transaction_pooler(url, "session") is False
    assert is_transaction_pooler(url.replace(":6543/", ":5432/"), "transaction")


def test_production_engine_requires_ssl_and_uses_bounded_pool() -> None:
    options = database_engine_options(_production_settings())

    assert options["connect_args"] == {
        "connect_timeout": 5,
        "sslmode": "require",
        "prepare_threshold": None,
    }
    assert options["pool_pre_ping"] is True
    assert options["pool_size"] == 2
    assert options["max_overflow"] == 1
    assert options["pool_timeout"] == 10
    assert options["pool_recycle"] == 300


class _Result:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _Connection:
    def __init__(self, value: int) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def execute(self, _statement) -> _Result:
        return _Result(self.value)


class _Engine:
    def __init__(self, value: int = 1, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    def connect(self) -> _Connection:
        if self.error:
            raise self.error
        return _Connection(self.value)


def test_database_readiness_succeeds_for_select_one() -> None:
    assert database_is_ready(_Engine()) is True


def test_database_readiness_fails_without_leaking_driver_error(caplog) -> None:
    assert database_is_ready(_Engine(error=RuntimeError("secret-password"))) is False
    assert "secret-password" not in caplog.text
