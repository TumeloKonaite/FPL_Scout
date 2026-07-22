from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
