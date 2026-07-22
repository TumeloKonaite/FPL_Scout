from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from src.app.infrastructure.models import Base, TranscriptRevision, TranscriptStatus
from src.app.infrastructure.transcript_repository import TranscriptRepository


@pytest.fixture
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'transcripts.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = [datetime(2026, 7, 21, tzinfo=timezone.utc)]
    return TranscriptRepository(factory, retry_hours=24, now=lambda: now[0]), factory, now


def test_available_transcript_is_retrievable_with_one_revision(repository) -> None:
    repo, factory, _ = repository
    saved = repo.save_available(video_id="abc123", transcript_text=" Hello   world ")

    assert repo.get_by_video_id("abc123").transcript_text == "Hello world"
    assert saved.content_hash
    with factory() as session:
        assert session.scalar(select(func.count(TranscriptRevision.id))) == 1


def test_identical_save_does_not_duplicate_revision_but_change_does(repository) -> None:
    repo, _, _ = repository
    saved = repo.save_available(video_id="abc123", transcript_text="same text")
    repo.save_available(video_id="abc123", transcript_text=" same   text ")
    assert len(repo.list_history(saved.id)) == 1

    repo.save_available(video_id="abc123", transcript_text="changed text")
    assert len(repo.list_history(saved.id)) == 2


def test_failure_is_persisted_and_obeys_retry_window(repository) -> None:
    repo, _, now = repository
    failure = repo.save_failure(
        video_id="missing", status=TranscriptStatus.UNAVAILABLE,
        failure_code="disabled", failure_reason=" captions   disabled ",
    )
    assert failure.failure_reason == "captions disabled"
    assert repo.should_retry(failure) is False

    now[0] += timedelta(hours=24)
    assert repo.should_retry(failure) is True


def test_invalid_failure_rolls_back_transaction(repository) -> None:
    repo, _, _ = repository
    with pytest.raises(ValueError):
        repo.save_failure(
            video_id="bad", status=TranscriptStatus.AVAILABLE,
            failure_code=None, failure_reason=None,
        )
    assert repo.get_by_video_id("bad") is None
