from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from src.app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from src.app.domain.reports.service import ReportService


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_report_service() -> ReportService:
    from src.app.domain.reports.service import ReportService

    return ReportService()
