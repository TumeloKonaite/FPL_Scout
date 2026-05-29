from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.adapters.transcript_api import load_webshare_proxy_settings
from src.app.core.config import get_settings
from src.services.pipeline_service import PipelineRunResult, run_pipeline_sync


@dataclass(frozen=True)
class StreamlitPipelineOptions:
    gameweek: int
    per_expert_limit: int = 2
    expert_name: str | None = None
    expert_count: int | None = None
    synthesis_enabled: bool = True
    base_runs_dir: Path = field(default_factory=lambda: Path(get_settings().REPORTS_DIR))
    output_dir: Path | None = None


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def build_streamlit_output_dir(
    *,
    gameweek: int,
    base_runs_dir: str | Path | None = None,
) -> Path:
    base_dir = Path(base_runs_dir or get_settings().REPORTS_DIR)
    return base_dir / f"gw{gameweek}-streamlit-{_timestamp_slug()}"


def run_pipeline_from_streamlit(options: StreamlitPipelineOptions) -> PipelineRunResult:
    load_dotenv()
    proxy_settings = load_webshare_proxy_settings()
    output_dir = options.output_dir or build_streamlit_output_dir(
        gameweek=options.gameweek,
        base_runs_dir=options.base_runs_dir,
    )

    return run_pipeline_sync(
        gameweek=options.gameweek,
        output_dir=output_dir,
        per_expert_limit=options.per_expert_limit,
        expert_name=options.expert_name,
        expert_count=options.expert_count,
        synthesis_enabled=options.synthesis_enabled,
        proxy_settings=proxy_settings,
    )
