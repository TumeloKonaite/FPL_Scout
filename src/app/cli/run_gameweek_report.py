from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from dotenv import load_dotenv

from src.adapters.transcript_api import load_webshare_proxy_settings
from src.services.pipeline_service import PipelineServiceError, run_pipeline_sync
from src.schemas.report_identity import validate_gameweek, validate_season


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.app.cli.run_gameweek_report",
        description="Run the automated FPL gameweek report pipeline from YouTube expert sources.",
    )
    parser.add_argument(
        "--gameweek",
        type=lambda value: validate_gameweek(int(value)),
        required=True,
        help="Gameweek number to run (1-38).",
    )
    parser.add_argument(
        "--season",
        type=validate_season,
        required=True,
        help="FPL season in YYYY-YY format.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where run artifacts will be written.",
    )
    parser.add_argument(
        "--per-expert-limit",
        type=int,
        default=2,
        help="Maximum number of recent videos to inspect per configured expert channel.",
    )
    parser.add_argument(
        "--expert-name",
        type=str,
        help="Restrict ingestion to one configured expert by exact name.",
    )
    parser.add_argument(
        "--expert-count",
        type=int,
        help="Restrict ingestion to the first N configured experts.",
    )
    parser.add_argument(
        "--no-synthesis",
        action="store_true",
        help="Skip final LLM synthesis and write a deterministic fallback final report instead.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    proxy_settings = load_webshare_proxy_settings()

    try:
        result = run_pipeline_sync(
            season=args.season,
            gameweek=args.gameweek,
            output_dir=args.output_dir,
            per_expert_limit=args.per_expert_limit,
            expert_name=args.expert_name,
            expert_count=args.expert_count,
            synthesis_enabled=not args.no_synthesis,
            proxy_settings=proxy_settings,
        )
    except PipelineServiceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: unexpected pipeline failure: {exc}", file=sys.stderr)
        return 1

    success_count = len(result.expert_outputs)
    failure_count = len(result.failed_jobs)
    synthesis_label = "disabled" if args.no_synthesis else "enabled"

    print(
        "Pipeline completed successfully for "
        f"{args.season} gameweek {args.gameweek}. "
        f"Discovered {len(result.discovered_videos)} video(s), "
        f"built {len(result.input_jobs)} job(s), "
        f"processed {success_count}/{len(result.input_jobs)} job(s); "
        f"synthesis {synthesis_label}. "
        f"Artifacts written to {result.run_path}."
    )
    print(f"Human-readable report: {result.run_path / 'report.md'}")
    if failure_count:
        print(
            f"Warning: {failure_count} job(s) failed during orchestration.",
            file=sys.stderr,
        )
    if result.transcript_failures:
        print(
            f"Warning: {len(result.transcript_failures)} transcript fetch(es) were unusable during ingestion.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
