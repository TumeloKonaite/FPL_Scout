from __future__ import annotations

from unittest.mock import patch

from src.app.cli.run_gameweek_report import build_parser, main
from src.adapters.transcript_api import WebshareProxySettings
from src.schemas.aggregate_report import DisagreementReport
from src.schemas.expert_analysis import ExpertVideoAnalysis
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport
from src.schemas.video_job import VideoAnalysisJob
from src.services.pipeline_service import PipelineRunResult, PipelineServiceError


def _build_job() -> VideoAnalysisJob:
    return VideoAnalysisJob(
        expert_name="Expert A",
        video_title="GW32 Preview",
        published_at="2026-04-09T12:00:00Z",
        gameweek=32,
        transcript="A transcript long enough for testing.",
        video_url="https://youtube.com/watch?v=expert-a",
    )


def _build_analysis() -> ExpertVideoAnalysis:
    return ExpertVideoAnalysis(
        expert_name="Expert A",
        video_title="GW32 Preview",
        gameweek=32,
        summary="Summary",
        key_takeaways=["Target Arsenal attackers"],
        recommended_players=["Bukayo Saka"],
        avoid_players=["Ollie Watkins"],
        captaincy_picks=["Mohamed Salah"],
        chip_strategy="wildcard",
        reasoning=["Fixtures"],
        confidence="high",
    )


def _build_aggregate_report() -> AggregatedFPLReport:
    return AggregatedFPLReport(
        season="2025-26",
        gameweek=32,
        expert_count=1,
        player_consensus=[],
        captaincy_consensus=[],
        transfer_consensus=[],
        fixture_insights=[],
        chip_strategy_consensus=[],
        disagreements=DisagreementReport(),
        conditional_advice=[],
        wait_for_news=[],
    )


def _build_final_report() -> FinalGameweekReport:
    return FinalGameweekReport(
        season="2025-26",
        gameweek=32,
        overview="Overview",
        transfers=[],
        captaincy=[],
        chip_strategy=[],
        fixture_notes=[],
        disagreements=[],
        conditional_advice=[],
        wait_for_news=[],
        expert_team_reveals=[],
        conclusion="Conclusion",
    )


def test_argument_parsing_supports_required_inputs_and_no_synthesis_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--gameweek",
            "32",
            "--season",
            "2025-26",
            "--output-dir",
            "runs/gw32",
            "--per-expert-limit",
            "3",
            "--expert-name",
            "FPL Harry",
            "--expert-count",
            "1",
            "--no-synthesis",
        ]
    )

    assert args.gameweek == 32
    assert str(args.output_dir) == "runs/gw32"
    assert args.per_expert_limit == 3
    assert args.expert_name == "FPL Harry"
    assert args.expert_count == 1
    assert args.no_synthesis is True


def test_cli_loads_dotenv_before_reading_proxy_settings(tmp_path) -> None:
    output_dir = tmp_path / "runs" / "gw32"
    result = PipelineRunResult(
        run_path=output_dir,
        season="2025-26",
        gameweek=32,
        discovered_videos=[],
        input_jobs=[],
        expert_outputs=[],
        aggregate_report=_build_aggregate_report(),
        final_report=_build_final_report(),
        failed_jobs=[],
        synthesis_enabled=True,
        transcript_failures=[],
        configured_experts=0,
    )
    events: list[str] = []

    def _fake_load_dotenv() -> None:
        events.append("dotenv")

    def _fake_load_proxy_settings() -> WebshareProxySettings:
        events.append("proxy")
        return WebshareProxySettings(enabled=False)

    with patch(
        "src.app.cli.run_gameweek_report.load_dotenv",
        side_effect=_fake_load_dotenv,
    ), patch(
        "src.app.cli.run_gameweek_report.load_webshare_proxy_settings",
        side_effect=_fake_load_proxy_settings,
    ), patch(
        "src.app.cli.run_gameweek_report.run_pipeline_sync",
        return_value=result,
    ):
        main(
            [
                "--gameweek",
                "32",
                "--season",
                "2025-26",
                "--output-dir",
                str(output_dir),
            ]
        )

    assert events == ["dotenv", "proxy"]


def test_cli_smoke_test_reports_success_and_passes_expected_arguments(capsys, tmp_path) -> None:
    output_dir = tmp_path / "runs" / "gw32"
    proxy_settings = WebshareProxySettings(
        enabled=True,
        proxy_username="proxy-user",
        proxy_password="proxy-pass",
    )
    result = PipelineRunResult(
        run_path=output_dir,
        season="2025-26",
        gameweek=32,
        discovered_videos=[
            {
                "video_id": "expert-a",
                "title": "GW32 Preview",
                "video_url": "https://youtube.com/watch?v=expert-a",
                "published_at": "2026-04-09T12:00:00Z",
                "expert_name": "Expert A",
            }
        ],
        input_jobs=[_build_job()],
        expert_outputs=[_build_analysis()],
        aggregate_report=_build_aggregate_report(),
        final_report=_build_final_report(),
        failed_jobs=[],
        synthesis_enabled=True,
        transcript_failures=[],
        configured_experts=5,
    )

    with patch(
        "src.app.cli.run_gameweek_report.load_webshare_proxy_settings",
        return_value=proxy_settings,
    ), patch("src.app.cli.run_gameweek_report.run_pipeline_sync", return_value=result) as mocked_run:
        exit_code = main(
            [
                "--gameweek",
                "32",
                "--season",
                "2025-26",
                "--output-dir",
                str(output_dir),
                "--per-expert-limit",
                "4",
                "--expert-name",
                "FPL Harry",
                "--expert-count",
                "1",
            ]
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Pipeline completed successfully for 2025-26 gameweek 32." in captured.out
    assert str(output_dir) in captured.out
    assert "report.md" in captured.out
    assert captured.err == ""
    mocked_run.assert_called_once_with(
        season="2025-26",
        gameweek=32,
        output_dir=output_dir,
        per_expert_limit=4,
        archive_limit=200,
        gameweek_deadline=None,
        expert_name="FPL Harry",
        expert_count=1,
        synthesis_enabled=True,
        proxy_settings=proxy_settings,
    )


def test_cli_end_to_end_mocked_pipeline_run_persists_outputs(tmp_path) -> None:
    output_dir = tmp_path / "runs" / "gw32"
    job = _build_job()
    analysis = _build_analysis()
    aggregate_report = _build_aggregate_report()
    final_report = _build_final_report()
    discovered_videos = [
        {
            "video_id": "expert-a",
            "title": job.video_title,
            "video_url": job.video_url or "",
            "published_at": job.published_at,
            "expert_name": job.expert_name,
        }
    ]

    async def fake_orchestration(jobs: list[VideoAnalysisJob]):
        class _Result:
            def __init__(self) -> None:
                self.results = [
                    type(
                        "RunResult",
                        (),
                        {"success": True, "analysis": analysis, "job": jobs[0], "error": None},
                    )()
                ]

        return _Result()

    with patch(
        "src.services.pipeline_service.ingest_youtube_video_jobs",
        return_value=type(
            "IngestionResult",
            (),
            {
                "configured_experts": 5,
                "discovered_videos": discovered_videos,
                "input_jobs": [job],
                "transcript_failures": [],
                "videos_discovered": 1,
                "videos_selected": 1,
            },
        )(),
    ), patch(
        "src.services.pipeline_service.run_gameweek_orchestration",
        side_effect=fake_orchestration,
    ), patch(
        "src.services.pipeline_service.build_aggregated_fpl_report",
        return_value=aggregate_report,
    ), patch(
        "src.services.pipeline_service.synthesize_final_report",
        return_value=final_report,
    ):
        exit_code = main(
            [
                "--gameweek",
                "32",
                "--season",
                "2025-26",
                "--output-dir",
                str(output_dir),
            ]
        )

    assert exit_code == 0
    assert (output_dir / "discovered_videos.json").exists()
    assert (output_dir / "input_jobs.json").exists()
    assert (output_dir / "expert_outputs.json").exists()
    assert (output_dir / "aggregate_report.json").exists()
    assert (output_dir / "final_report.json").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "report.md").exists()


def test_cli_returns_readable_failure_message(capsys, tmp_path) -> None:
    with patch(
        "src.app.cli.run_gameweek_report.run_pipeline_sync",
        side_effect=PipelineServiceError(
            "Pipeline could not create any usable video analysis jobs from YouTube sources."
        ),
    ):
        exit_code = main(
            [
                "--gameweek",
                "32",
                "--season",
                "2025-26",
                "--output-dir",
                str(tmp_path / "runs" / "gw32"),
            ]
        )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip() == "Error: Pipeline could not create any usable video analysis jobs from YouTube sources."
