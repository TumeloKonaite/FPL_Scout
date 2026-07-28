from types import SimpleNamespace

from src.app.cli import run_gameweek_report
from src.app.cli.run_gameweek_report import build_parser


def test_cli_accepts_database_run_id_instead_of_output_path() -> None:
    args = build_parser().parse_args(
        ["--season", "2025-26", "--gameweek", "32", "--run-id", "run-32"]
    )
    assert args.run_id == "run-32"
    assert not hasattr(args, "output_dir")


def test_cli_injects_catalogue_provider(monkeypatch) -> None:
    provider = object()
    captured = {}
    monkeypatch.setattr(
        run_gameweek_report, "get_player_catalogue_provider", lambda: provider
    )
    monkeypatch.setattr(
        run_gameweek_report, "load_webshare_proxy_settings", lambda: None
    )

    def run(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            expert_outputs=[],
            failed_jobs=[],
            discovered_videos=[],
            input_jobs=[],
            transcript_failures=[],
            run_path="run-31",
        )

    monkeypatch.setattr(run_gameweek_report, "run_pipeline_sync", run)

    exit_code = run_gameweek_report.main(
        ["--season", "2025-26", "--gameweek", "31", "--no-synthesis"]
    )

    assert exit_code == 0
    assert captured["player_catalogue_provider"] is provider
