from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.adapters.storage import build_manifest, create_run_folder, load_json, save_json, save_text
from src.app.core.config import get_settings
from src.services.report_formatter_service import format_gameweek_markdown_report


ARTIFACT_FILENAMES = {
    "aggregate_report": "aggregate_report.json",
    "discovered_videos": "discovered_videos.json",
    "expert_outputs": "expert_outputs.json",
    "final_report": "final_report.json",
    "input_jobs": "input_jobs.json",
    "report_markdown": "report.md",
}

MANIFEST_FILENAME = "manifest.json"


def _created_at_for_run_path(run_path: Path) -> str:
    stat = run_path.stat()
    created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ReportService:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or get_settings().REPORTS_DIR)

    def _resolve_run_path(self, run_dir: str | Path | None = None) -> Path:
        if run_dir is None:
            return create_run_folder(base_dir=self.base_dir)

        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        return run_path

    def persist_run(
        self,
        *,
        discovered_videos: list[Any] | None = None,
        input_jobs: list[Any],
        expert_outputs: list[Any],
        aggregate_report: Any,
        final_report: Any,
        failed_jobs: list[Any] | None = None,
        duplicate_sources: list[Any] | None = None,
        input_mode: str = "youtube_auto",
        configured_experts: int | None = None,
        videos_discovered: int | None = None,
        videos_selected: int | None = None,
        jobs_created: int | None = None,
        transcript_failures: list[Any] | None = None,
        run_dir: str | Path | None = None,
    ) -> Path:
        run_path = self._resolve_run_path(run_dir)
        artifact_paths = {
            artifact_name: run_path / filename
            for artifact_name, filename in ARTIFACT_FILENAMES.items()
        }
        markdown_report = format_gameweek_markdown_report(aggregate_report, final_report)

        save_json(artifact_paths["discovered_videos"], discovered_videos or [])
        save_json(artifact_paths["input_jobs"], input_jobs)
        save_json(artifact_paths["expert_outputs"], expert_outputs)
        save_json(artifact_paths["aggregate_report"], aggregate_report)
        save_json(artifact_paths["final_report"], final_report)
        save_text(artifact_paths["report_markdown"], markdown_report)

        manifest = build_manifest(
            run_id=run_path.name,
            created_at=_created_at_for_run_path(run_path),
            artifacts=ARTIFACT_FILENAMES,
            input_jobs=input_jobs,
            expert_outputs=expert_outputs,
            failed_jobs=failed_jobs,
            duplicate_sources=duplicate_sources,
            input_mode=input_mode,
            configured_experts=configured_experts,
            videos_discovered=videos_discovered,
            videos_selected=videos_selected,
            jobs_created=jobs_created,
            transcript_failures=transcript_failures,
        )
        save_json(run_path / MANIFEST_FILENAME, manifest)

        return run_path

    def load_run(self, run_path: str | Path) -> dict[str, Any]:
        resolved_run_path = Path(run_path)
        manifest = load_json(resolved_run_path / MANIFEST_FILENAME)
        if not isinstance(manifest, dict):
            raise TypeError("Run manifest must be a JSON object")

        artifacts = manifest.get("artifacts", {})
        if not isinstance(artifacts, dict):
            raise TypeError("Run manifest artifacts must be a JSON object")

        loaded_artifacts = {
            artifact_name: (
                load_json(resolved_run_path / filename)
                if str(filename).endswith(".json")
                else (resolved_run_path / filename).read_text(encoding="utf-8")
            )
            for artifact_name, filename in artifacts.items()
        }

        return {
            "run_path": resolved_run_path,
            "manifest": manifest,
            **loaded_artifacts,
        }


def persist_run(
    *,
    discovered_videos: list[Any] | None = None,
    input_jobs: list[Any],
    expert_outputs: list[Any],
    aggregate_report: Any,
    final_report: Any,
    failed_jobs: list[Any] | None = None,
    duplicate_sources: list[Any] | None = None,
    input_mode: str = "youtube_auto",
    configured_experts: int | None = None,
    videos_discovered: int | None = None,
    videos_selected: int | None = None,
    jobs_created: int | None = None,
    transcript_failures: list[Any] | None = None,
    base_dir: str | Path | None = None,
    run_dir: str | Path | None = None,
) -> Path:
    return ReportService(base_dir=base_dir).persist_run(
        discovered_videos=discovered_videos,
        input_jobs=input_jobs,
        expert_outputs=expert_outputs,
        aggregate_report=aggregate_report,
        final_report=final_report,
        failed_jobs=failed_jobs,
        duplicate_sources=duplicate_sources,
        input_mode=input_mode,
        configured_experts=configured_experts,
        videos_discovered=videos_discovered,
        videos_selected=videos_selected,
        jobs_created=jobs_created,
        transcript_failures=transcript_failures,
        run_dir=run_dir,
    )


def load_run(run_path: str | Path) -> dict[str, Any]:
    return ReportService().load_run(run_path)
