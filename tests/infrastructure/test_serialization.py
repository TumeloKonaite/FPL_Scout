from __future__ import annotations

from src.app.infrastructure.serialization import to_json_value


def test_to_json_value_removes_null_characters_recursively() -> None:
    value = {
        "video\x00_title": "14 VALUE Players for Gameweek 1 \x00",
        "nested": [
            {"transcript": "first\x00second"},
            "clean value",
        ],
    }

    assert to_json_value(value) == {
        "video_title": "14 VALUE Players for Gameweek 1 ",
        "nested": [
            {"transcript": "firstsecond"},
            "clean value",
        ],
    }
