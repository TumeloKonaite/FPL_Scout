from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import ValidationError

from src.app.domain.reports.suggested_team import validate_consensus_squad
from src.schemas.final_report import FinalGameweekReport


@dataclass(frozen=True)
class PublicGameweekIndexMetadata:
    has_report: bool
    has_suggested_team: bool


def normalize_legacy_final_report(final_report: object) -> dict[str, Any]:
    """Return a compatibility-normalized copy of a stored report snapshot."""
    if not isinstance(final_report, Mapping):
        raise TypeError("final_report must be a JSON object")
    snapshot: dict[str, Any] = deepcopy(dict(final_report))
    suggested = snapshot.get("suggested_team")
    if not isinstance(suggested, dict) or "constructionMethod" in suggested:
        return snapshot

    has_lineup = bool(
        suggested.get("startingXi")
        or suggested.get("starters")
        or suggested.get("players")
    )
    suggested["constructionMethod"] = (
        "legacy_snapshot" if has_lineup else "insufficient_evidence"
    )
    suggested["consensusStrength"] = "insufficient"
    suggested["provenanceAvailable"] = False
    suggested["provenance"] = None
    if has_lineup:
        suggested["constructionStatus"] = "consensus"
    return snapshot


def public_gameweek_index_metadata(
    final_report: object,
) -> PublicGameweekIndexMetadata:
    """Derive immutable selector metadata when a report snapshot is stored.

    ``final_report`` remains the source of truth.  The returned value is persisted
    beside the snapshot and refreshed whenever a processing snapshot is replaced,
    so public index reads never need to deserialize the report JSONB.
    """
    try:
        report = FinalGameweekReport.model_validate(
            normalize_legacy_final_report(final_report)
        )
    except (TypeError, ValidationError):
        return PublicGameweekIndexMetadata(False, False)
    return PublicGameweekIndexMetadata(
        has_report=True,
        has_suggested_team=(
            report.suggested_team is not None
            and validate_consensus_squad(report.suggested_team)
        ),
    )


__all__ = [
    "PublicGameweekIndexMetadata",
    "normalize_legacy_final_report",
    "public_gameweek_index_metadata",
]
