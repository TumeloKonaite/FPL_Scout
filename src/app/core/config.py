from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini")

    DATA_DIR: str = Field(default="data")
    REPORTS_DIR: str = Field(default="data/reports")
    RAW_DATA_DIR: str = Field(default="data/raw")
    PROCESSED_DATA_DIR: str = Field(default="data/processed")
    TRANSCRIPTS_DIR: str = Field(default="data/transcripts")
    RUNS_DIR: str = Field(default="data/runs")

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
    TRANSCRIPT_STORE: str = Field(default="postgres")
    TRANSCRIPT_FILE_FALLBACK_ENABLED: bool = Field(default=True)
    TRANSCRIPT_FAILURE_RETRY_HOURS: int = Field(default=24, ge=0)

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
    def derive_data_subdirectories(self) -> "Settings":
        data_dir = str(self.DATA_DIR)
        derived = {
            "REPORTS_DIR": f"{data_dir}/reports",
            "RAW_DATA_DIR": f"{data_dir}/raw",
            "PROCESSED_DATA_DIR": f"{data_dir}/processed",
            "TRANSCRIPTS_DIR": f"{data_dir}/transcripts",
            "RUNS_DIR": f"{data_dir}/runs",
        }
        for field_name, value in derived.items():
            configured = getattr(self, field_name)
            default = type(self).model_fields[field_name].default
            if field_name not in self.model_fields_set or configured == default:
                setattr(self, field_name, value)
        return self

    @model_validator(mode="after")
    def validate_production_database(self) -> "Settings":
        if self.ENVIRONMENT.casefold() != "production":
            return self

        if self.TRANSCRIPT_STORE.casefold() != "postgres":
            raise ValueError("production requires TRANSCRIPT_STORE=postgres")
        if self.TRANSCRIPT_FILE_FALLBACK_ENABLED:
            raise ValueError(
                "production requires TRANSCRIPT_FILE_FALLBACK_ENABLED=false"
            )
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

    @property
    def runtime_directories(self) -> tuple[str, ...]:
        return (
            self.REPORTS_DIR,
            self.RAW_DATA_DIR,
            self.PROCESSED_DATA_DIR,
            self.TRANSCRIPTS_DIR,
            self.RUNS_DIR,
        )


def bootstrap_data_directories(app_settings: Settings | None = None) -> None:
    resolved_settings = app_settings or get_settings()
    for directory in resolved_settings.runtime_directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
