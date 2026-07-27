from src.app.cli.run_gameweek_report import build_parser


def test_cli_accepts_database_run_id_instead_of_output_path() -> None:
    args = build_parser().parse_args(
        ["--season", "2025-26", "--gameweek", "32", "--run-id", "run-32"]
    )
    assert args.run_id == "run-32"
    assert not hasattr(args, "output_dir")
