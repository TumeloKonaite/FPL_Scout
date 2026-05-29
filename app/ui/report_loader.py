from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.adapters.storage import load_json
from src.app.core.config import settings
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport


DEFAULT_RUNS_DIR = Path(settings.REPORTS_DIR)


@dataclass(frozen=True)
class ReportBundle:
    run_dir: Path
    final_report_path: Path
    aggregate_report_path: Path | None
    final_report: FinalGameweekReport
    aggregate_report: AggregatedFPLReport | None


def parse_streamlit_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", dest="input_path")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    return parser.parse_known_args(argv)[0]


def find_latest_run_dir(base_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    if not base_dir.exists():
        raise FileNotFoundError(f"Runs directory does not exist: {base_dir}")

    candidate_dirs = [
        path
        for path in base_dir.iterdir()
        if path.is_dir() and (path / "final_report.json").exists()
    ]
    if not candidate_dirs:
        raise FileNotFoundError(
            f"No run folders containing final_report.json were found in {base_dir}"
        )

    return max(
        candidate_dirs,
        key=lambda path: ((path / "final_report.json").stat().st_mtime, path.name),
    )


def resolve_report_paths(
    input_path: str | Path | None = None,
    runs_dir: str | Path = DEFAULT_RUNS_DIR,
) -> tuple[Path, Path, Path | None]:
    base_dir = Path(runs_dir)

    if input_path is None:
        run_dir = find_latest_run_dir(base_dir)
        final_report_path = run_dir / "final_report.json"
    else:
        requested = Path(input_path)
        if requested.is_dir():
            run_dir = requested
            final_report_path = run_dir / "final_report.json"
        else:
            final_report_path = requested
            run_dir = final_report_path.parent

    if not final_report_path.exists():
        raise FileNotFoundError(f"Could not find final report at {final_report_path}")

    aggregate_report_path = run_dir / "aggregate_report.json"
    if not aggregate_report_path.exists():
        aggregate_report_path = None

    return run_dir, final_report_path, aggregate_report_path


def load_report_bundle(
    input_path: str | Path | None = None,
    runs_dir: str | Path = DEFAULT_RUNS_DIR,
) -> ReportBundle:
    run_dir, final_report_path, aggregate_report_path = resolve_report_paths(
        input_path=input_path,
        runs_dir=runs_dir,
    )

    final_report = FinalGameweekReport.model_validate(load_json(final_report_path))
    aggregate_report = None
    if aggregate_report_path is not None:
        aggregate_report = AggregatedFPLReport.model_validate(load_json(aggregate_report_path))

    return ReportBundle(
        run_dir=run_dir,
        final_report_path=final_report_path,
        aggregate_report_path=aggregate_report_path,
        final_report=final_report,
        aggregate_report=aggregate_report,
    )


def load_raw_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = load_json(path)
    return payload if isinstance(payload, dict) else None
