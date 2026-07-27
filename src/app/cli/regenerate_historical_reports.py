from __future__ import annotations

import argparse
import json
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.adapters.transcript_api import load_webshare_proxy_settings
from src.schemas.report_identity import validate_gameweek, validate_season
from src.services.historical_regeneration_service import (
    HistoricalRegenerationService,
    parse_deadline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.app.cli.regenerate_historical_reports",
        description=(
            "Inventory and safely regenerate historical FPL reports with "
            "independent source validation and atomic supersession."
        ),
    )
    parser.add_argument("--season", type=validate_season, required=True)
    parser.add_argument(
        "--from-gameweek",
        type=lambda value: validate_gameweek(int(value)),
        required=True,
    )
    parser.add_argument(
        "--to-gameweek",
        type=lambda value: validate_gameweek(int(value)),
        required=True,
    )
    parser.add_argument("--deadlines-file", type=Path, required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Produce a contamination inventory without changing report state.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--batch-identifier")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--allow-identical-fingerprint", action="store_true")
    parser.add_argument("--override-justification")
    parser.add_argument("--per-expert-limit", type=int, default=2)
    parser.add_argument("--archive-limit", type=int, default=200)
    parser.add_argument("--expert-name")
    parser.add_argument("--expert-count", type=int)
    parser.add_argument("--no-synthesis", action="store_true")
    return parser


def load_deadlines(path: Path, season: str) -> dict[int, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load deadlines file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Deadlines file must contain a JSON object")
    if "season" in payload and payload["season"] != season:
        raise ValueError(
            f"Deadlines file is for {payload['season']}, not {season}"
        )
    values: Any = payload.get("deadlines", payload.get("gameweeks", payload))
    if not isinstance(values, dict):
        raise ValueError("Deadlines must be an object keyed by gameweek")
    deadlines: dict[int, str] = {}
    for key, value in values.items():
        if not str(key).isdigit():
            continue
        gameweek = validate_gameweek(int(key))
        deadline = (
            value.get("deadline")
            if isinstance(value, dict)
            else value
        )
        if not isinstance(deadline, str):
            raise ValueError(f"Gameweek {gameweek} has no string deadline")
        parse_deadline(deadline)
        deadlines[gameweek] = deadline
    return deadlines


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.from_gameweek > args.to_gameweek:
        parser.error("--from-gameweek must not exceed --to-gameweek")
    if args.allow_identical_fingerprint and not args.override_justification:
        parser.error(
            "--override-justification is required with "
            "--allow-identical-fingerprint"
        )
    try:
        deadlines = load_deadlines(args.deadlines_file, args.season)
        command_args = list(argv) if argv is not None else sys.argv[1:]
        command = shlex.join(
            [
                "python",
                "-m",
                "src.app.cli.regenerate_historical_reports",
                *command_args,
            ]
        )
        summary = HistoricalRegenerationService().regenerate(
            season=args.season,
            from_gameweek=args.from_gameweek,
            to_gameweek=args.to_gameweek,
            deadlines=deadlines,
            command=command,
            batch_identifier=args.batch_identifier,
            dry_run=args.dry_run,
            continue_on_error=args.continue_on_error,
            allow_identical_fingerprint=args.allow_identical_fingerprint,
            override_justification=args.override_justification,
            pipeline_options={
                "per_expert_limit": args.per_expert_limit,
                "archive_limit": args.archive_limit,
                "expert_name": args.expert_name,
                "expert_count": args.expert_count,
                "synthesis_enabled": not args.no_synthesis,
                "proxy_settings": load_webshare_proxy_settings(),
            },
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if summary.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
