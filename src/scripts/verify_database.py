from __future__ import annotations

import json

from sqlalchemy import func, inspect, select

from src.app.infrastructure.database import get_engine, get_session_factory
from src.app.infrastructure.models import Transcript, TranscriptRevision

EXPECTED_INDEXES = {
    "transcripts": {
        "ix_transcripts_video_id",
        "ix_transcripts_status",
        "ix_transcripts_updated_at",
        "ix_transcripts_fetched_at",
    },
    "transcript_revisions": {"ix_transcript_revisions_transcript_id"},
}


def verify_database_schema() -> dict[str, int]:
    engine = get_engine()
    inspector = inspect(engine)
    missing_tables = set(EXPECTED_INDEXES) - set(inspector.get_table_names())
    if missing_tables:
        raise RuntimeError(
            "Missing database tables: " + ", ".join(sorted(missing_tables))
        )

    for table, expected in EXPECTED_INDEXES.items():
        actual = {index["name"] for index in inspector.get_indexes(table)}
        missing = expected - actual
        if missing:
            raise RuntimeError(
                f"Missing indexes for {table}: " + ", ".join(sorted(missing))
            )

    session_factory = get_session_factory()
    with session_factory() as session:
        transcripts = session.scalar(select(func.count(Transcript.id))) or 0
        revisions = session.scalar(select(func.count(TranscriptRevision.id))) or 0
        orphan_revisions = (
            session.scalar(
                select(func.count(TranscriptRevision.id))
                .outerjoin(
                    Transcript,
                    Transcript.id == TranscriptRevision.transcript_id,
                )
                .where(Transcript.id.is_(None))
            )
            or 0
        )
    if orphan_revisions:
        raise RuntimeError(
            f"Found {orphan_revisions} transcript revisions without a transcript"
        )
    return {
        "transcripts": transcripts,
        "transcript_revisions": revisions,
        "orphan_revisions": orphan_revisions,
    }


def main() -> None:
    print(json.dumps(verify_database_schema(), sort_keys=True))


if __name__ == "__main__":
    main()
