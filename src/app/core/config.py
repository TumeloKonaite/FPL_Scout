from functools import lru_cache
from typing import List, Literal

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini")

    DATABASE_URL: str = Field(default="")
    DIRECT_DATABASE_URL: str = Field(default="")
    DATABASE_POOL_MODE: Literal["auto", "direct", "session", "transaction"] = Field(
        default="auto"
    )
    DATABASE_POOL_SIZE: int = Field(default=2, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=1, ge=0)
    DATABASE_POOL_TIMEOUT_SECONDS: int = Field(default=10, ge=1)
    DATABASE_POOL_RECYCLE_SECONDS: int = Field(default=300, ge=1)
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = Field(default=5, ge=1)
    TRANSCRIPT_FAILURE_RETRY_HOURS: int = Field(default=24, ge=0)

    REDIS_URL: str = Field(default="")
    PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS: int = Field(default=300, ge=1)
    PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS: int = Field(
        default=604_800, ge=1
    )
    PUBLIC_RECOMMENDATION_CURRENT_SWR_SECONDS: int = Field(default=60, ge=0)
    PUBLIC_RECOMMENDATION_HISTORICAL_SWR_SECONDS: int = Field(
        default=86_400, ge=0
    )
    PUBLIC_RECOMMENDATION_RECENT_GAMEWEEKS: int = Field(default=1, ge=0, le=38)
    PUBLIC_RECOMMENDATION_REDIS_TIMEOUT_SECONDS: float = Field(
        default=0.2, gt=0
    )

    VIDEO_SELECTION_WINDOW_DAYS_BEFORE: int = Field(default=10, ge=0)
    VIDEO_SELECTION_WINDOW_DAYS_AFTER: int = Field(default=2, ge=0)

    PIPELINE_API_TOKEN: str = Field(default="")
    ADMIN_API_TOKEN: str = Field(default="")

    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    ENVIRONMENT: str = Field(default="development")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_public_recommendation_cache_policy(self) -> "Settings":
        if (
            self.PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS
            <= self.PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS
        ):
            raise ValueError(
                "PUBLIC_RECOMMENDATION_HISTORICAL_TTL_SECONDS must be greater "
                "than PUBLIC_RECOMMENDATION_CURRENT_TTL_SECONDS"
            )
        return self

    @model_validator(mode="after")
    def validate_production_database(self) -> "Settings":
        if self.ENVIRONMENT.casefold() != "production":
            return self

        for name in ("DATABASE_URL", "DIRECT_DATABASE_URL"):
            value = getattr(self, name).strip()
            if not value:
                raise ValueError(f"production requires {name}")
            try:
                url = make_url(value)
            except Exception as exc:
                raise ValueError(f"{name} must be a valid PostgreSQL URL") from exc
            if url.drivername not in {
                "postgres",
                "postgresql",
                "postgresql+psycopg",
            }:
                raise ValueError(f"{name} must be a PostgreSQL URL")

        direct_url = make_url(self.DIRECT_DATABASE_URL)
        if direct_url.port == 6543:
            raise ValueError(
                "DIRECT_DATABASE_URL cannot use a transaction pooler; use the "
                "direct endpoint or session pooler on port 5432"
            )
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
