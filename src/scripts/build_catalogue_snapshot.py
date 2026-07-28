from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


POSITIONS = {"1": "GK", "2": "DEF", "3": "MID", "4": "FWD"}


def build_snapshot(
    *,
    season: str,
    players_path: Path,
    teams_path: Path,
    source: str,
    retrieved_at: str,
    aliases_path: Path | None = None,
) -> dict:
    teams = {
        row["id"]: row["name"]
        for row in csv.DictReader(teams_path.open(encoding="utf-8"))
    }
    aliases: dict[str, list[str]] = {}
    if aliases_path is not None:
        alias_payload = json.loads(aliases_path.read_text(encoding="utf-8"))
        if alias_payload.get("season") != season:
            raise ValueError("Alias configuration season does not match snapshot")
        aliases = alias_payload.get("aliases", {})

    players = []
    for row in csv.DictReader(players_path.open(encoding="utf-8")):
        player_id = int(row["id"])
        canonical_name = " ".join(
            value.strip()
            for value in (row.get("first_name", ""), row.get("second_name", ""))
            if value.strip()
        )
        players.append(
            {
                "playerId": player_id,
                "canonicalName": canonical_name or row["web_name"],
                "displayName": row["web_name"],
                "team": teams.get(row["team"]),
                "position": POSITIONS[row["element_type"]],
                "price": int(row["now_cost"]) / 10,
                "aliases": aliases.get(str(player_id), []),
            }
        )
    players.sort(key=lambda item: item["playerId"])
    content_hash = sha256(
        json.dumps(players, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schemaVersion": 1,
        "snapshotId": f"{season}:{content_hash}",
        "season": season,
        "source": source,
        "retrievedAt": retrieved_at,
        "players": players,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True)
    parser.add_argument("--players", type=Path, required=True)
    parser.add_argument("--teams", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--aliases", type=Path)
    parser.add_argument("--retrieved-at")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = build_snapshot(
        season=args.season,
        players_path=args.players,
        teams_path=args.teams,
        source=args.source,
        retrieved_at=args.retrieved_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        aliases_path=args.aliases,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
