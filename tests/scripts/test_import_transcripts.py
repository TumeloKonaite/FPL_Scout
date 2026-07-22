import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.infrastructure.models import Base
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.scripts.import_transcripts import import_transcript_directory


def test_import_is_idempotent_and_continues_past_malformed_json(tmp_path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "abc.json").write_text(
        json.dumps({"video_id": "abc", "transcript": " Hello   world "}), encoding="utf-8"
    )
    (source / "broken.json").write_text("{broken", encoding="utf-8")
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    Base.metadata.create_all(engine)
    repo = TranscriptRepository(sessionmaker(bind=engine, expire_on_commit=False))

    first = import_transcript_directory(source, repository=repo)
    second = import_transcript_directory(source, repository=repo)

    assert (first.imported, first.malformed) == (1, 1)
    assert (second.skipped, second.malformed) == (1, 1)
    assert len(repo.list_history(repo.get_by_video_id("abc").id)) == 1


def test_dry_run_does_not_write(tmp_path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "abc.json").write_text('{"transcript":"text"}', encoding="utf-8")
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    Base.metadata.create_all(engine)
    repo = TranscriptRepository(sessionmaker(bind=engine, expire_on_commit=False))

    summary = import_transcript_directory(source, repository=repo, dry_run=True)

    assert summary.imported == 1
    assert repo.get_by_video_id("abc") is None
