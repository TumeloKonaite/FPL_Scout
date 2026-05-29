from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.ui.pipeline_runner import (
    StreamlitPipelineOptions,
    build_streamlit_output_dir,
    run_pipeline_from_streamlit,
)


def test_build_streamlit_output_dir_uses_gameweek_and_runs_base() -> None:
    output_dir = build_streamlit_output_dir(gameweek=32, base_runs_dir="custom-runs")

    assert output_dir.parent == Path("custom-runs")
    assert output_dir.name.startswith("gw32-streamlit-")


def test_run_pipeline_from_streamlit_calls_domain_service(tmp_path) -> None:
    output_dir = tmp_path / "runs" / "gw32"
    response = {
        "status": "completed",
        "result": {"run_path": output_dir},
        "error": None,
    }

    with patch("app.ui.pipeline_runner.load_dotenv") as mocked_load_dotenv, patch(
        "app.ui.pipeline_runner.load_webshare_proxy_settings",
        return_value=None,
    ) as mocked_proxy_settings, patch(
        "app.ui.pipeline_runner.run_pipeline",
        return_value=response,
    ) as mocked_run:
        result = run_pipeline_from_streamlit(
            StreamlitPipelineOptions(
                gameweek=32,
                per_expert_limit=3,
                expert_name="Expert A",
                expert_count=1,
                synthesis_enabled=False,
                output_dir=output_dir,
            )
        )

    assert result == response
    mocked_load_dotenv.assert_called_once_with()
    mocked_proxy_settings.assert_called_once_with()
    mocked_run.assert_called_once_with(
        gameweek=32,
        output_dir=output_dir,
        per_expert_limit=3,
        expert_name="Expert A",
        expert_count=1,
        synthesis_enabled=False,
        proxy_settings=None,
    )
