from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.app.core.config import get_settings
from src.app.infrastructure.storage.report_store import ReportStore, update_report_index
from src.schemas.report_identity import validate_gameweek, validate_season


ARTIFACT_NAMES = ("final_report.json", "aggregate_report.json", "manifest.json")


@dataclass
class BackfillResult:
    migrated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read {path.name} as JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _encoded(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()


def _migrate_run(run_dir: Path, season: str, base_dir: Path) -> bool:
    paths = [run_dir / name for name in ARTIFACT_NAMES if (run_dir / name).exists()]
    final_path = run_dir / "final_report.json"
    manifest_path = run_dir / "manifest.json"
    if final_path not in paths:
        raise ValueError("final_report.json is missing")

    payloads = {path: _load_object(path) for path in paths}
    final = payloads[final_path]
    gameweek = validate_gameweek(final.get("gameweek"))
    existing = {
        value
        for payload in payloads.values()
        if isinstance((value := payload.get("season")), str) and value
    }
    if len(existing) > 1 or (existing and season not in existing):
        raise ValueError(f"existing season metadata conflicts with {season}")
    if existing and all(
        payload.get("season") == season for payload in payloads.values()
    ):
        return False

    for path, payload in payloads.items():
        artifact_gameweek = payload.get("gameweek")
        if (
            artifact_gameweek is not None
            and validate_gameweek(artifact_gameweek) != gameweek
        ):
            raise ValueError(f"{path.name} gameweek conflicts with final_report.json")
        payload["season"] = season
        payload["gameweek"] = gameweek

    if manifest_path not in payloads:
        raise ValueError("manifest.json is missing")

    backups = {path: path.read_bytes() for path in paths}
    index_path = base_dir / "index.json"
    index_backup = index_path.read_bytes() if index_path.exists() else None
    temporary_paths: list[Path] = []
    try:
        for path, payload in payloads.items():
            temporary = path.with_suffix(f"{path.suffix}.{os.getpid()}.backfill")
            temporary.write_bytes(_encoded(payload))
            temporary_paths.append(temporary)
        for path, temporary in zip(payloads, temporary_paths, strict=True):
            os.replace(temporary, path)
        store = ReportStore(base_dir)
        update_report_index(base_dir, store.get_report(run_dir))
    except Exception:
        for path, content in backups.items():
            path.write_bytes(content)
        if index_backup is None:
            index_path.unlink(missing_ok=True)
        else:
            index_path.write_bytes(index_backup)
        raise
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)
    return True


def backfill_report_seasons(
    base_dir: str | Path,
    *,
    season: str,
    dry_run: bool = False,
) -> BackfillResult:
    if season != "unknown":
        validate_season(season)
    root = Path(base_dir)
    result = BackfillResult()
    if not root.exists():
        result.failed[str(root)] = "reports directory does not exist"
        return result

    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        final_path = run_dir / "final_report.json"
        if not final_path.exists():
            continue
        try:
            payload = _load_object(final_path)
            current = payload.get("season")
            if current is not None and current != season:
                result.skipped.append(run_dir.name)
                continue
            validate_gameweek(payload.get("gameweek"))
            if dry_run:
                result.migrated.append(run_dir.name)
            elif _migrate_run(run_dir, season, root):
                result.migrated.append(run_dir.name)
            else:
                result.skipped.append(run_dir.name)
        except (OSError, ValueError, TypeError) as exc:
            result.failed[run_dir.name] = str(exc)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assign explicit seasons to legacy report artifacts."
    )
    parser.add_argument(
        "--season", required=True, help="YYYY-YY, or 'unknown' for manual review"
    )
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports_dir = args.reports_dir or Path(get_settings().REPORTS_DIR)
    try:
        result = backfill_report_seasons(
            reports_dir, season=args.season, dry_run=args.dry_run
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2
    action = "Would migrate" if args.dry_run else "Migrated"
    for run_id in result.migrated:
        print(f"{action}: {run_id}")
    for run_id in result.skipped:
        print(f"Skipped: {run_id}")
    for run_id, error in result.failed.items():
        print(f"Failed: {run_id}: {error}")
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
