from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.adapters.fpl import get_player_catalogue_provider
from src.app.domain.reports.player_catalogue import PlayerCatalogueProvider
from src.app.infrastructure.report_repository import (
    ReportNotFoundError,
    ReportRepository,
)
from src.services.pipeline_service import PipelineRunResult, run_pipeline_sync
from src.services.provenance_validation_service import (
    VALIDATION_RULE_VERSION,
    fingerprint_overlap,
    selected_video_fingerprint,
    validate_selected_sources,
)
from src.services.report_service import ReportService


PipelineRunner = Callable[..., PipelineRunResult]
DEFAULT_OVERLAP_WARNING_THRESHOLD = 0.75


def parse_deadline(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"Invalid ISO-8601 deadline: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Deadline must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def _row_sources(row: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    discovered = [
        dict(item) for item in row.discovered_videos if isinstance(item, dict)
    ]
    jobs = [dict(item) for item in row.input_jobs if isinstance(item, dict)]
    if not jobs:
        jobs = [
            {
                "video_id": item.get("video_id", ""),
                "video_title": item.get("title", ""),
                "video_url": item.get("video_url", ""),
                "published_at": item.get("published_at", ""),
                "description": item.get("description", ""),
                "transcript": item.get("transcript", ""),
            }
            for item in discovered
            if item.get("selected")
        ]
    return discovered, jobs


def build_contamination_inventory(
    *,
    repository: ReportRepository,
    season: str,
    from_gameweek: int,
    to_gameweek: int,
    deadlines: dict[int, str],
) -> dict[str, Any]:
    rows = repository.reports_for_range(
        season,
        from_gameweek,
        to_gameweek,
        statuses=("completed",),
    )
    reports: list[dict[str, Any]] = []
    for row in rows:
        deadline = deadlines.get(row.gameweek)
        discovered, jobs = _row_sources(row)
        validations = validate_selected_sources(
            gameweek=row.gameweek,
            season=row.season,
            gameweek_deadline=deadline,
            input_jobs=jobs,
            discovered_videos=discovered,
        )
        fingerprint, video_ids = selected_video_fingerprint(validations)
        invalid = [item for item in validations if not item.get("selected")]
        reports.append(
            {
                "season": row.season,
                "gameweek": row.gameweek,
                "run_id": row.run_id,
                "status": row.status,
                "historical_deadline": deadline,
                "source_count": len(jobs),
                "selected_video_ids": video_ids,
                "selected_video_fingerprint": fingerprint,
                "validation_rule_version": VALIDATION_RULE_VERSION,
                "validation_passed": not invalid,
                "source_validations": validations,
                "provenance_classification": (
                    "verified" if not invalid else "contaminated_or_unverifiable"
                ),
            }
        )
    covered = {item["gameweek"] for item in reports}
    missing_gameweeks = [
        gameweek
        for gameweek in range(from_gameweek, to_gameweek + 1)
        if gameweek not in covered
    ]
    return {
        "mode": "dry-run-inventory",
        "season": season,
        "from_gameweek": from_gameweek,
        "to_gameweek": to_gameweek,
        "report_count": len(reports),
        "missing_gameweeks": missing_gameweeks,
        "reports": reports,
    }


class HistoricalRegenerationService:
    def __init__(
        self,
        repository: ReportRepository | None = None,
        *,
        pipeline_runner: PipelineRunner = run_pipeline_sync,
        player_catalogue_provider: PlayerCatalogueProvider | None = None,
    ) -> None:
        self.repository = repository or ReportRepository()
        self.pipeline_runner = pipeline_runner
        self.player_catalogue_provider = (
            player_catalogue_provider or get_player_catalogue_provider()
        )

    def regenerate(
        self,
        *,
        season: str,
        from_gameweek: int,
        to_gameweek: int,
        deadlines: dict[int, str],
        command: str,
        batch_identifier: str | None = None,
        dry_run: bool = False,
        continue_on_error: bool = False,
        allow_identical_fingerprint: bool = False,
        override_justification: str | None = None,
        overlap_warning_threshold: float = DEFAULT_OVERLAP_WARNING_THRESHOLD,
        pipeline_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        batch_id = batch_identifier or str(uuid4())
        inventory = build_contamination_inventory(
            repository=self.repository,
            season=season,
            from_gameweek=from_gameweek,
            to_gameweek=to_gameweek,
            deadlines=deadlines,
        )
        if dry_run:
            return {
                **inventory,
                "batch_identifier": batch_id,
                "command": command,
            }
        if allow_identical_fingerprint and not (
            override_justification and override_justification.strip()
        ):
            raise ValueError(
                "An override justification is required when identical "
                "fingerprints are allowed"
            )

        results: list[dict[str, Any]] = []
        seen: dict[int, tuple[str, list[str]]] = {}
        options = dict(pipeline_options or {})
        for gameweek in range(from_gameweek, to_gameweek + 1):
            deadline_value = deadlines.get(gameweek)
            if not deadline_value:
                results.append(
                    {
                        "gameweek": gameweek,
                        "status": "failed",
                        "error": "missing_historical_deadline",
                    }
                )
                if not continue_on_error:
                    break
                continue
            deadline = parse_deadline(deadline_value)

            reusable = self._find_reusable_replacement(
                season=season,
                gameweek=gameweek,
                deadline=deadline,
            )
            if reusable is not None:
                fingerprint = str(
                    reusable.manifest.get("selected_video_fingerprint", "")
                )
                video_ids = [
                    str(value)
                    for value in reusable.manifest.get("selected_video_ids", [])
                ]
                seen[gameweek] = (fingerprint, video_ids)
                results.append(
                    {
                        "gameweek": gameweek,
                        "status": "skipped",
                        "reason": "validated_replacement_already_canonical",
                        "replacement_run_id": reusable.run_id,
                        "selected_video_fingerprint": fingerprint,
                    }
                )
                continue

            run_id = str(uuid4())
            report_service = ReportService(
                repository=self.repository,
                defer_publication=True,
            )
            try:
                self.pipeline_runner(
                    season=season,
                    gameweek=gameweek,
                    run_id=run_id,
                    gameweek_deadline=deadline_value,
                    report_service=report_service,
                    player_catalogue_provider=self.player_catalogue_provider,
                    **options,
                )
                replacement = self.repository.get(run_id)
                validations = list(
                    replacement.manifest.get("provenance_validation", [])
                )
                fingerprint = str(
                    replacement.manifest.get("selected_video_fingerprint", "")
                )
                video_ids = [
                    str(value)
                    for value in replacement.manifest.get(
                        "selected_video_ids", []
                    )
                ]
                collisions, overlaps = self._reuse_evidence(
                    gameweek=gameweek,
                    fingerprint=fingerprint,
                    video_ids=video_ids,
                    seen=seen,
                    threshold=overlap_warning_threshold,
                )
                if collisions and not allow_identical_fingerprint:
                    raise ValueError(
                        "identical_selected_video_fingerprint:"
                        + ",".join(str(value) for value in collisions)
                    )
                prior = self.repository.completed_for_gameweek(
                    season, gameweek
                )
                audit_data = {
                    "season": season,
                    "gameweek": gameweek,
                    "previous_run_ids": [row.run_id for row in prior],
                    "replacement_run_id": run_id,
                    "previous_report_statuses": {
                        row.run_id: row.status for row in prior
                    },
                    "replacement_report_status": "completed",
                    "historical_deadline": deadline.isoformat(),
                    "selected_video_ids": video_ids,
                    "selected_videos": [
                        {
                            "video_id": item.get("video_id"),
                            "title": item.get("video_title"),
                            "url": item.get("video_url"),
                            "validation": item,
                        }
                        for item in validations
                    ],
                    "validation_rule_version": VALIDATION_RULE_VERSION,
                    "generation_timestamp": replacement.created_at.isoformat(),
                    "supersession_timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "batch_identifier": batch_id,
                    "command": command,
                    "identical_fingerprint_gameweeks": collisions,
                    "high_overlap_gameweeks": overlaps,
                    "fingerprint_override": (
                        {
                            "allowed": True,
                            "justification": override_justification,
                        }
                        if collisions and allow_identical_fingerprint
                        else {"allowed": False}
                    ),
                }
                superseded = self.repository.publish_replacement(
                    replacement_run_id=run_id,
                    historical_deadline=deadline,
                    batch_identifier=batch_id,
                    command=command,
                    supersession_reason=(
                        "Regenerated after historical source-provenance "
                        "contamination remediation"
                    ),
                    validation_rule_version=VALIDATION_RULE_VERSION,
                    selected_video_fingerprint=fingerprint,
                    audit_data=audit_data,
                )
                seen[gameweek] = (fingerprint, video_ids)
                results.append(
                    {
                        "gameweek": gameweek,
                        "status": "completed",
                        "previous_run_ids": superseded,
                        "replacement_run_id": run_id,
                        "resolved_canonical_run_id": run_id,
                        "canonical_verified": True,
                        "historical_deadline": deadline.isoformat(),
                        "selected_video_ids": video_ids,
                        "selected_video_fingerprint": fingerprint,
                        "identical_fingerprint_gameweeks": collisions,
                        "high_overlap_gameweeks": overlaps,
                    }
                )
            except Exception as exc:
                try:
                    self.repository.invalidate_processing(run_id, str(exc))
                except (ReportNotFoundError, ValueError):
                    pass
                results.append(
                    {
                        "gameweek": gameweek,
                        "status": "failed",
                        "replacement_run_id": run_id,
                        "error": str(exc),
                    }
                )
                if not continue_on_error:
                    break

        return {
            "mode": "regeneration",
            "batch_identifier": batch_id,
            "command": command,
            "season": season,
            "from_gameweek": from_gameweek,
            "to_gameweek": to_gameweek,
            "validation_rule_version": VALIDATION_RULE_VERSION,
            "inventory": inventory,
            "results": results,
            "completed": sum(item["status"] == "completed" for item in results),
            "skipped": sum(item["status"] == "skipped" for item in results),
            "failed": sum(item["status"] == "failed" for item in results),
        }

    def _find_reusable_replacement(
        self, *, season: str, gameweek: int, deadline: datetime
    ) -> Any | None:
        for row in reversed(
            self.repository.completed_for_gameweek(season, gameweek)
        ):
            regeneration = row.manifest.get("regeneration", {})
            validations = row.manifest.get("provenance_validation", [])
            stored_deadline = regeneration.get(
                "historical_deadline",
                row.manifest.get("gameweek_deadline"),
            )
            if (
                regeneration
                and stored_deadline
                and parse_deadline(str(stored_deadline)) == deadline
                and validations
                and all(item.get("selected") for item in validations)
                and regeneration.get("validation_rule_version")
                == VALIDATION_RULE_VERSION
            ):
                return row
        return None

    @staticmethod
    def _reuse_evidence(
        *,
        gameweek: int,
        fingerprint: str,
        video_ids: list[str],
        seen: dict[int, tuple[str, list[str]]],
        threshold: float,
    ) -> tuple[list[int], list[dict[str, Any]]]:
        collisions: list[int] = []
        overlaps: list[dict[str, Any]] = []
        for other_gameweek, (other_fingerprint, other_ids) in seen.items():
            if fingerprint and fingerprint == other_fingerprint:
                collisions.append(other_gameweek)
            overlap = fingerprint_overlap(video_ids, other_ids)
            if overlap >= threshold:
                overlaps.append(
                    {
                        "gameweek": other_gameweek,
                        "overlap": overlap,
                        "adjacent": abs(gameweek - other_gameweek) == 1,
                    }
                )
        return collisions, overlaps
