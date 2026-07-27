"""One-time, idempotent import of legacy report and pipeline JSON into PostgreSQL.

This script is operational migration tooling only. Application code never calls it.
Remove it after the documented retention window closes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from src.app.infrastructure.database import get_session_factory
from src.app.infrastructure.models import CompletedReportRun, PipelineRun
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport


@dataclass
class ImportResult:
    pipeline_runs_imported: int = 0
    reports_imported: int = 0
    skipped_existing: int = 0
    malformed: dict[str, str] = field(default_factory=dict)


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _array(path: Path) -> list[Any]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("expected a JSON array")
    return value


def _timestamp(value: Any, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def migrate_legacy_storage(
    reports_dir: Path,
    runs_dir: Path,
    *,
    dry_run: bool = False,
) -> ImportResult:
    result = ImportResult()
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        known_pipeline_ids = set(session.scalars(select(PipelineRun.run_id)))
        for path in sorted(runs_dir.glob("*.json")) if runs_dir.exists() else []:
            try:
                payload = _object(path)
                run_id = str(payload.get("run_id") or path.stem)
                if run_id in known_pipeline_ids:
                    result.skipped_existing += 1
                    continue
                status = str(payload.get("status") or "failed")
                status = "queued" if status == "pending" else status
                if status not in {"queued", "running", "completed", "failed"}:
                    raise ValueError(f"unsupported status {status!r}")
                created = _timestamp(
                    payload.get("created_at"),
                    datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
                )
                completed = (
                    _timestamp(payload.get("completed_at"), created)
                    if payload.get("completed_at")
                    else None
                )
                stored_result = payload.get("result")
                if isinstance(stored_result, dict) and stored_result.get("run_path"):
                    stored_result = {
                        **stored_result,
                        "run_path": Path(str(stored_result["run_path"])).name,
                    }
                if not dry_run:
                    session.add(
                        PipelineRun(
                            run_id=run_id,
                            status=status,
                            current_stage=payload.get("current_stage"),
                            input_data=payload.get("input_data") or {},
                            result=stored_result,
                            error=payload.get("error"),
                            created_at=created,
                            started_at=(
                                _timestamp(payload.get("started_at"), created)
                                if payload.get("started_at")
                                else None
                            ),
                            updated_at=_timestamp(payload.get("updated_at"), created),
                            completed_at=completed,
                            duration_seconds=payload.get("duration_seconds"),
                        )
                    )
                known_pipeline_ids.add(run_id)
                result.pipeline_runs_imported += 1
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                result.malformed[str(path)] = str(exc)

        known_report_ids = set(session.scalars(select(CompletedReportRun.run_id)))
        run_dirs = (
            sorted(path for path in reports_dir.iterdir() if path.is_dir())
            if reports_dir.exists()
            else []
        )
        for run_dir in run_dirs:
            try:
                final_payload = _object(run_dir / "final_report.json")
                aggregate_payload = _object(run_dir / "aggregate_report.json")
                final = FinalGameweekReport.model_validate(final_payload)
                aggregate = AggregatedFPLReport.model_validate(aggregate_payload)
                if (final.season, final.gameweek) != (
                    aggregate.season,
                    aggregate.gameweek,
                ):
                    raise ValueError("aggregate/final report identity mismatch")
                manifest_path = run_dir / "manifest.json"
                manifest = _object(manifest_path) if manifest_path.exists() else {}
                run_id = str(manifest.get("run_id") or run_dir.name)
                if run_id in known_report_ids:
                    result.skipped_existing += 1
                    continue
                pipeline_run_id = next(
                    (
                        candidate
                        for candidate in known_pipeline_ids
                        if run_id == candidate or run_id.endswith(candidate)
                    ),
                    None,
                )
                created = _timestamp(
                    manifest.get("created_at"),
                    datetime.fromtimestamp(
                        (run_dir / "final_report.json").stat().st_mtime,
                        timezone.utc,
                    ),
                )
                updated = _timestamp(manifest.get("updated_at"), created)
                if not dry_run:
                    session.add(
                        CompletedReportRun(
                            run_id=run_id,
                            pipeline_run_id=pipeline_run_id,
                            season=final.season,
                            gameweek=final.gameweek,
                            status="completed",
                            discovered_videos=_array(run_dir / "discovered_videos.json"),
                            input_jobs=_array(run_dir / "input_jobs.json"),
                            expert_outputs=_array(run_dir / "expert_outputs.json"),
                            failed_jobs=manifest.get("failed_jobs") or [],
                            duplicate_sources=manifest.get("duplicate_sources") or [],
                            transcript_failures=manifest.get("transcript_failures") or [],
                            aggregate_report=aggregate.model_dump(mode="json"),
                            final_report=final.model_dump(mode="json"),
                            manifest=manifest,
                            rendered_markdown=(
                                (run_dir / "report.md").read_text(encoding="utf-8")
                                if (run_dir / "report.md").exists()
                                else None
                            ),
                            created_at=created,
                            updated_at=updated,
                            completed_at=updated,
                        )
                    )
                known_report_ids.add(run_id)
                result.reports_imported += 1
            except (
                OSError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
                ValidationError,
            ) as exc:
                result.malformed[str(run_dir)] = str(exc)
        if dry_run:
            session.rollback()
    return result


def verify_import() -> dict[str, Any]:
    with get_session_factory() as session:
        identities = list(
            session.execute(
                select(
                    CompletedReportRun.run_id,
                    CompletedReportRun.season,
                    CompletedReportRun.gameweek,
                ).where(CompletedReportRun.status == "completed")
            )
        )
        return {
            "pipeline_runs": session.scalar(select(func.count(PipelineRun.run_id))) or 0,
            "reports": len(identities),
            "report_identities": [
                {"run_id": run_id, "season": season, "gameweek": gameweek}
                for run_id, season, gameweek in identities
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = migrate_legacy_storage(
        args.reports_dir, args.runs_dir, dry_run=args.dry_run
    )
    print(json.dumps({**result.__dict__, "verification": verify_import()}, indent=2))
    return 1 if result.malformed else 0


if __name__ == "__main__":
    raise SystemExit(main())
