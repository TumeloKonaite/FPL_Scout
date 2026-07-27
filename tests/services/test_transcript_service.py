from pathlib import Path

import pytest

from src.adapters.transcript_api import TranscriptFetchError
from src.services.transcript_service import get_clean_transcript
from src.utils.text_cleaning import clean_transcript


@pytest.fixture(autouse=True)
def isolate_unit_tests_from_configured_database(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.transcript_service._default_repository",
        lambda: None,
    )


def test_clean_transcript_normalizes_whitespace() -> None:
    raw_text = "  Hello   world\n\nthis\t is   a test  "

    assert clean_transcript(raw_text) == "Hello world this is a test"


def test_get_clean_transcript_returns_available_payload(monkeypatch) -> None:
    fixture_path = Path("tests/fixtures/sample_transcript_1.txt")
    raw_text = fixture_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda video_id, proxy_settings=None: raw_text,
    )

    payload = get_clean_transcript("abc123")

    assert payload == {
        "video_id": "abc123",
        "transcript": "Hello and welcome to the FPL roundup for gameweek 12.",
        "status": "available",
    }


def test_get_clean_transcript_returns_missing_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda video_id, proxy_settings=None: "",
    )

    payload = get_clean_transcript("missing-video")

    assert payload == {
        "video_id": "missing-video",
        "transcript": "",
        "status": "missing",
    }


def test_get_clean_transcript_returns_error_payload_when_fetch_retries_exhausted(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda video_id, proxy_settings=None: (_ for _ in ()).throw(
            TranscriptFetchError(f"provider unavailable for {video_id}")
        ),
    )

    payload = get_clean_transcript("broken-video")

    assert payload["video_id"] == "broken-video"
    assert payload["transcript"] == ""
    assert payload["status"] == "error"
    assert "failed after 3 attempt(s)" in payload["error"]


def test_get_clean_transcript_uses_cached_payload_without_fetching(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "transcripts"
    cache_dir.mkdir(parents=True)
    (cache_dir / "abc123.json").write_text(
        '{\n'
        '  "video_id": "abc123",\n'
        '  "transcript": "Cached transcript",\n'
        '  "status": "available"\n'
        '}',
        encoding="utf-8",
    )

    def _unexpected_fetch(video_id, proxy_settings=None):
        raise AssertionError("fetch_transcript should not be called on cache hit")

    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        _unexpected_fetch,
    )

    payload = get_clean_transcript("abc123", cache_dir=cache_dir)

    assert payload == {
        "video_id": "abc123",
        "transcript": "Cached transcript",
        "status": "available",
    }


def test_get_clean_transcript_sleeps_and_caches_successful_fetch(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "transcripts"
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "src.services.transcript_service.random.uniform",
        lambda start, end: 1.5,
    )
    monkeypatch.setattr(
        "src.services.transcript_service.time.sleep",
        lambda seconds: captured.setdefault("sleep", seconds),
    )
    monkeypatch.setattr(
        "src.services.transcript_service.fetch_transcript",
        lambda video_id, proxy_settings=None: "  Hello   world  ",
    )

    payload = get_clean_transcript("cache-me", cache_dir=cache_dir)

    assert payload == {
        "video_id": "cache-me",
        "transcript": "Hello world",
        "status": "available",
    }
    assert captured == {"sleep": 1.5}
    assert (cache_dir / "cache-me.json").exists()
