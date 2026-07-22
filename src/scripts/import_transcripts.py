from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.app.infrastructure.models import TranscriptStatus
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.utils.text_cleaning import clean_transcript


@dataclass(slots=True)
class ImportSummary:
    scanned: int = 0
    imported: int = 0
    skipped: int = 0
    malformed: int = 0


def import_transcript_directory(
    source: str | Path,
    *,
    repository: TranscriptRepository,
    dry_run: bool = False,
) -> ImportSummary:
    summary = ImportSummary()
    for path in sorted(Path(source).glob("*.json")):
        summary.scanned += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload is not a JSON object")
            video_id = payload.get("video_id") or path.stem
            transcript = payload.get("transcript", payload.get("transcript_text"))
            if not isinstance(video_id, str) or not video_id.strip():
                raise ValueError("video_id is missing")
            if not isinstance(transcript, str) or not transcript.strip():
                raise ValueError("transcript text is missing")
            normalized = clean_transcript(transcript)
            existing = repository.get_by_video_id(video_id)
            if (
                existing is not None
                and existing.status == TranscriptStatus.AVAILABLE
                and existing.transcript_text == normalized
            ):
                summary.skipped += 1
                continue
            if not dry_run:
                repository.save_available(
                    video_id=video_id,
                    transcript_text=normalized,
                    video_url=payload.get("video_url"),
                    title=payload.get("title"),
                    expert=payload.get("expert"),
                    source_language=payload.get("source_language"),
                )
            summary.imported += 1
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            summary.malformed += 1
            print(f"{path}: {exc}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy transcript JSON files")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = import_transcript_directory(
        args.source,
        repository=TranscriptRepository(),
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(summary), sort_keys=True))


if __name__ == "__main__":
    main()
