from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.infrastructure.models import Base, TranscriptStatus
from src.app.infrastructure.transcript_repository import TranscriptRepository
from src.services.transcript_service import get_clean_transcript


def _repository(tmp_path) -> TranscriptRepository:
    engine = create_engine(f"sqlite:///{tmp_path / 'transcripts.db'}")
    Base.metadata.create_all(engine)
    return TranscriptRepository(sessionmaker(bind=engine, expire_on_commit=False))


def test_database_cache_hit_avoids_youtube_fetch(monkeypatch, tmp_path) -> None:
    repository = _repository(tmp_path)
    saved = repository.save_available(video_id="cached", transcript_text="Stored text")
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    payload = get_clean_transcript("cached", repository=repository, cache_dir=tmp_path / "legacy")

    assert payload["transcript"] == "Stored text"
    assert payload["transcript_id"] == str(saved.id)
    assert payload["transcript_revision_id"]


def test_database_cache_miss_fetches_and_persists(monkeypatch, tmp_path) -> None:
    repository = _repository(tmp_path)
    monkeypatch.setattr("src.services.transcript_service.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda video_id, proxy_settings=None: " New   transcript ",
    )

    payload = get_clean_transcript("new", repository=repository, cache_dir=tmp_path / "legacy")

    assert payload["status"] == "available"
    assert repository.get_by_video_id("new").transcript_text == "New transcript"
    assert not (tmp_path / "legacy" / "new.json").exists()


def test_unavailable_database_record_is_reused_before_retry(monkeypatch, tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.save_failure(
        video_id="missing", status=TranscriptStatus.UNAVAILABLE,
        failure_code="empty", failure_reason="No captions",
    )
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
    )

    payload = get_clean_transcript("missing", repository=repository)

    assert payload["status"] == "missing"
    assert payload["failure_code"] == "empty"
