from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from fastapi.testclient import TestClient

from src.app.infrastructure.report_repository import ReportRepository
from src.app.main import create_app
from src.schemas.report_identity import validate_gameweek, validate_season
from src.services.provenance_validation_service import VALIDATION_RULE_VERSION


def verify(
    *,
    season: str,
    from_gameweek: int,
    to_gameweek: int,
    repository: ReportRepository | None = None,
) -> dict:
    reports = repository or ReportRepository()
    client = TestClient(create_app())
    results = []
    for gameweek in range(from_gameweek, to_gameweek + 1):
        canonical_record = reports.latest_public_recommendation(season, gameweek)
        if canonical_record is None:
            raise RuntimeError(
                f"No published report for {season} gameweek {gameweek}"
            )
        canonical = reports.get(canonical_record.run_id)
        response = client.get(
            "/api/recommendations",
            params={"season": season, "gameweek": gameweek},
        )
        payload = response.json()
        regeneration = canonical.manifest.get("regeneration", {})
        validations = canonical.manifest.get("provenance_validation", [])
        verified = (
            response.status_code == 200
            and payload.get("season") == season
            and payload.get("gameweek") == gameweek
            and regeneration.get("validation_rule_version")
            == VALIDATION_RULE_VERSION
            and validations
            and all(item.get("selected") for item in validations)
        )
        results.append(
            {
                "season": season,
                "gameweek": gameweek,
                "http_status": response.status_code,
                "response_season": payload.get("season"),
                "response_gameweek": payload.get("gameweek"),
                "resolved_run_id": canonical.run_id,
                "validation_rule_version": regeneration.get(
                    "validation_rule_version"
                ),
                "source_count": len(validations),
                "verified": verified,
            }
        )
    return {
        "season": season,
        "from_gameweek": from_gameweek,
        "to_gameweek": to_gameweek,
        "verified": all(item["verified"] for item in results),
        "results": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args(argv)
    if args.from_gameweek > args.to_gameweek:
        parser.error("--from-gameweek must not exceed --to-gameweek")
    summary = verify(
        season=args.season,
        from_gameweek=args.from_gameweek,
        to_gameweek=args.to_gameweek,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
