from __future__ import annotations

from src.app.domain.reports.team_of_week import SuggestedTeamOfWeek


class _Column:
    def __enter__(self) -> "_Column":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_streamlit_team_of_week_renders_domain_result(monkeypatch) -> None:
    from app.ui import streamlit_app

    calls: list[str] = []

    monkeypatch.setattr(
        streamlit_app.st,
        "subheader",
        lambda *_args, **_kwargs: calls.append("subheader"),
    )
    monkeypatch.setattr(
        streamlit_app.st,
        "columns",
        lambda *_args, **_kwargs: [_Column(), _Column()],
    )
    monkeypatch.setattr(
        streamlit_app.st,
        "dataframe",
        lambda *_args, **_kwargs: calls.append("dataframe"),
    )
    monkeypatch.setattr(
        streamlit_app.st,
        "metric",
        lambda *_args, **_kwargs: calls.append("metric"),
    )
    monkeypatch.setattr(
        streamlit_app.st,
        "caption",
        lambda *_args, **_kwargs: calls.append("caption"),
    )

    team = SuggestedTeamOfWeek(
        starting_xi=["Bukayo Saka"],
        bench=["Cole Palmer"],
        captain="Bukayo Saka",
        vice_captain=None,
        player_votes={"Bukayo Saka": 2},
        bench_votes={"Cole Palmer": 1},
    )

    streamlit_app.render_suggested_team(team)

    assert calls.count("dataframe") == 2
    assert calls.count("metric") == 2
    assert streamlit_app.build_suggested_team_of_week.__module__ == (
        "src.app.domain.reports.team_of_week"
    )
