from __future__ import annotations

import math
import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from app.ui.pipeline_runner import StreamlitPipelineOptions, run_pipeline_from_streamlit
from app.ui.report_loader import (
    ReportBundle,
    load_report_bundle,
    parse_streamlit_args,
)
from src.app.domain.reports.team_of_week import (
    SuggestedTeamOfWeek,
    build_suggested_team_of_week,
)
from src.schemas.final_report import (
    FinalDisagreement,
    FinalExpertTeamReveal,
    FinalGameweekReport,
    FinalRecommendation,
)

st.set_page_config(
    page_title="FPL Gameweek Report",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }
        .app-shell {
            padding: 1.4rem 1.6rem;
            border-radius: 24px;
            background:
                radial-gradient(circle at top right, rgba(120, 196, 255, 0.18), transparent 30%),
                linear-gradient(145deg, rgba(8, 30, 52, 0.95), rgba(13, 71, 84, 0.92));
            color: #f8fafc;
            margin-bottom: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
        }
        .app-shell h1 {
            margin-bottom: 0.35rem;
            color: #f8fafc;
        }
        .muted {
            color: rgba(248, 250, 252, 0.78);
            font-size: 0.96rem;
        }
        .pill {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            margin: 0.15rem 0.35rem 0.15rem 0;
            border-radius: 999px;
            font-size: 0.9rem;
            font-weight: 600;
            background: #dbeafe;
            color: #0f172a;
        }
        .pill.buy {
            background: #dcfce7;
            color: #14532d;
        }
        .pill.sell {
            background: #fee2e2;
            color: #991b1b;
        }
        .recommendation-card {
            border-radius: 18px;
            padding: 1rem 1rem 0.95rem;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            margin-bottom: 0.85rem;
        }
        .recommendation-title {
            font-weight: 700;
            margin-bottom: 0.35rem;
            color: #0f172a;
        }
        .recommendation-note {
            color: #475569;
            font-size: 0.95rem;
            margin: 0;
        }
        .caption-kicker {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.76rem;
            color: #38bdf8;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def confidence_stars(confidence: float | None) -> str:
    if confidence is None:
        return "No score"
    stars = max(1, min(5, math.ceil(confidence * 5)))
    return " ".join(["★"] * stars)


def confidence_label(confidence: float | None) -> str:
    if confidence is None:
        return "n/a"
    return f"{confidence:.0%}"


def render_badges(items: list[str], kind: str = "buy") -> None:
    if not items:
        st.caption("None recorded.")
        return
    html = "".join(
        f'<span class="pill {escape(kind)}">{escape(item)}</span>'
        for item in items
    )
    st.markdown(html, unsafe_allow_html=True)


def render_recommendation_card(item: FinalRecommendation) -> None:
    title = escape(item.title)
    rationale = escape(item.rationale)
    label = escape(confidence_label(item.confidence))
    stars = escape(confidence_stars(item.confidence))
    st.markdown(
        f"""
        <div class="recommendation-card">
            <div class="recommendation-title">{title}</div>
            <p class="recommendation-note">{rationale}</p>
            <p class="recommendation-note"><strong>Confidence:</strong> {label} • {stars}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(report: FinalGameweekReport, bundle: ReportBundle) -> None:
    gw_label = f"Gameweek {report.gameweek}" if report.gameweek is not None else "Gameweek Report"
    st.markdown(
        f"""
        <div class="app-shell">
            <div class="caption-kicker">Fantasy Premier League</div>
            <h1>{escape(gw_label)} Expert Dashboard</h1>
            <p class="muted">{escape(report.overview)}</p>
            <p class="muted">Source: {escape(str(bundle.final_report_path))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_suggested_team(team: SuggestedTeamOfWeek | None) -> None:
    st.subheader("Suggested Team Of The Week")
    if team is None:
        st.info("No usable team reveal data was available to build a suggested XI.")
        return

    captain_label = team.captain or "Not specified"
    vice_label = team.vice_captain or "Not specified"
    starter_df = pd.DataFrame(
        [
            {
                "Player": player,
                "XI Votes": team.player_votes.get(player, 0),
                "Role": (
                    "Captain"
                    if player == team.captain
                    else "Vice-Captain"
                    if player == team.vice_captain
                    else "Starter"
                ),
            }
            for player in team.starting_xi
        ]
    )
    bench_df = pd.DataFrame(
        [
            {"Bench": player, "Bench Votes": team.bench_votes.get(player, 0)}
            for player in team.bench
        ]
    )

    left, right = st.columns([1.4, 1])
    with left:
        st.dataframe(starter_df, use_container_width=True, hide_index=True)
    with right:
        st.metric("Captain", captain_label)
        st.metric("Vice-Captain", vice_label)
        if not bench_df.empty:
            st.dataframe(bench_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No consensus bench available.")


def render_captaincy(captaincy: list[FinalRecommendation]) -> None:
    st.subheader("Captaincy")
    if not captaincy:
        st.info("No captaincy recommendations were generated for this run.")
        return

    columns = st.columns(min(3, len(captaincy)))
    for column, item in zip(columns, captaincy, strict=False):
        with column:
            st.metric(
                label=item.title,
                value=confidence_stars(item.confidence),
                help=item.rationale,
            )
            st.caption(f"Confidence: {confidence_label(item.confidence)}")


def render_transfers(transfers: list[FinalRecommendation]) -> None:
    st.subheader("Transfers")
    if not transfers:
        st.info("No transfer targets were surfaced in this run.")
        return
    for item in transfers:
        render_recommendation_card(item)


def render_risks(report: FinalGameweekReport) -> None:
    st.subheader("Risks")
    risks = list(report.wait_for_news) + list(report.conditional_advice)
    if not risks:
        st.info("No major wait-for-news flags were recorded.")
        return
    for item in risks:
        st.warning(item)


def render_chip_strategy(chips: list[FinalRecommendation]) -> None:
    st.subheader("Chip Strategy")
    if not chips:
        st.info("No chip strategy guidance was generated for this run.")
        return
    for index, item in enumerate(chips, start=1):
        st.info(f"Option {index}: {item.title}\n\n{item.rationale}")


def render_fixture_notes(notes: list[str]) -> None:
    st.subheader("Fixture Notes")
    if not notes:
        st.caption("No fixture-specific notes were captured.")
        return
    for note in notes:
        st.markdown(f"- {note}")


def render_disagreements(disagreements: list[FinalDisagreement]) -> None:
    st.subheader("Disagreements")
    if not disagreements:
        st.caption("No major disagreements highlighted.")
        return
    for item in disagreements:
        sides = ", ".join(item.sides) if item.sides else "No explicit sides listed."
        st.warning(f"{item.topic}: {item.summary}")
        st.caption(sides)


def render_expert_reveals(reveals: list[FinalExpertTeamReveal]) -> None:
    st.subheader("Expert Team Reveals")
    if not reveals:
        st.info("No expert team reveal data was available for this run.")
        return

    for reveal in reveals:
        title = reveal.expert_name
        if reveal.confidence is not None:
            title = f"{title} • {confidence_label(reveal.confidence)}"
        with st.expander(title, expanded=False):
            left, right = st.columns(2)
            with left:
                st.markdown("**Transfers In**")
                render_badges(reveal.transfers_in, kind="buy")
                st.markdown("**Transfers Out**")
                render_badges(reveal.transfers_out, kind="sell")
            with right:
                st.markdown(f"**Captain:** {reveal.captain or 'Not specified'}")
                st.markdown(f"**Vice-Captain:** {reveal.vice_captain or 'Not specified'}")
                st.markdown("**Notes**")
                st.write(reveal.summary or "No summary provided.")


def build_consensus_frames(bundle: ReportBundle) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    report = bundle.final_report
    captaincy_rows = [
        {
            "Captain": item.title,
            "Confidence": confidence_label(item.confidence),
            "Rationale": item.rationale,
        }
        for item in report.captaincy
    ]
    transfer_rows = [
        {
            "Transfer": item.title,
            "Confidence": confidence_label(item.confidence),
            "Rationale": item.rationale,
        }
        for item in report.transfers
    ]
    captaincy_df = pd.DataFrame(captaincy_rows) if captaincy_rows else None
    transfer_df = pd.DataFrame(transfer_rows) if transfer_rows else None
    return captaincy_df, transfer_df


def render_consensus_snapshot(bundle: ReportBundle) -> None:
    st.subheader("Consensus Snapshot")
    captaincy_df, transfer_df = build_consensus_frames(bundle)
    if captaincy_df is None and transfer_df is None:
        st.caption("No consensus table data available.")
        return

    left, right = st.columns(2)
    with left:
        if captaincy_df is not None:
            st.dataframe(captaincy_df, use_container_width=True, hide_index=True)
    with right:
        if transfer_df is not None:
            st.dataframe(transfer_df, use_container_width=True, hide_index=True)


def render_conclusion(conclusion: str) -> None:
    st.subheader("Conclusion")
    st.success(conclusion)


def render_pipeline_controls(default_gameweek: int | None, runs_dir: str) -> ReportBundle | None:
    st.sidebar.header("Run Pipeline")
    with st.sidebar.form("pipeline-run-form"):
        gameweek = st.number_input(
            "Gameweek",
            min_value=1,
            max_value=38,
            value=default_gameweek or 1,
            step=1,
        )
        per_expert_limit = st.number_input(
            "Videos per expert",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
        )
        expert_name = st.text_input("Expert name override", value="")
        expert_count_value = st.number_input(
            "Expert count override",
            min_value=0,
            max_value=50,
            value=0,
            step=1,
            help="Leave at 0 to use all configured experts.",
        )
        synthesis_enabled = st.checkbox("Enable final synthesis", value=True)
        submitted = st.form_submit_button("Generate Expert Dashboard", use_container_width=True)

    st.sidebar.caption("This runs the full YouTube-to-report pipeline and reloads the new run into the dashboard.")

    if not submitted:
        return None

    options = StreamlitPipelineOptions(
        gameweek=int(gameweek),
        per_expert_limit=int(per_expert_limit),
        expert_name=expert_name.strip() or None,
        expert_count=int(expert_count_value) or None,
        synthesis_enabled=synthesis_enabled,
        base_runs_dir=Path(runs_dir),
    )

    with st.spinner(f"Running pipeline for GW{options.gameweek}. This can take a little while..."):
        result = run_pipeline_from_streamlit(options)

    st.sidebar.success(f"Generated run: {result.run_path}")
    st.sidebar.caption(
        f"Processed {len(result.expert_outputs)}/{len(result.input_jobs)} jobs from "
        f"{len(result.discovered_videos)} discovered videos."
    )
    return load_report_bundle(input_path=result.run_path, runs_dir=runs_dir)


def main() -> None:
    inject_styles()
    args = parse_streamlit_args(sys.argv[1:])

    st.sidebar.header("Report Input")
    st.sidebar.code(
        args.input_path or f"Latest run from {args.runs_dir}/",
        language="text",
    )
    st.sidebar.caption(f"Pass `--input {args.runs_dir}/gw32/final_report.json` or a run directory.")

    try:
        bundle = load_report_bundle(input_path=args.input_path, runs_dir=args.runs_dir)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    try:
        refreshed_bundle = render_pipeline_controls(bundle.final_report.gameweek, args.runs_dir)
    except Exception as exc:
        st.sidebar.error(f"Pipeline failed: {exc}")
        refreshed_bundle = None

    bundle = refreshed_bundle or bundle
    report = bundle.final_report
    suggested_team = (
        build_suggested_team_of_week(bundle.aggregate_report.expert_team_reveals)
        if bundle.aggregate_report is not None
        else None
    )
    render_header(report, bundle)

    overview_tab, experts_tab, strategy_tab = st.tabs(["Overview", "Experts", "Strategy"])

    with overview_tab:
        render_suggested_team(suggested_team)
        st.divider()
        render_captaincy(report.captaincy)
        st.divider()
        left, right = st.columns([1.3, 1])
        with left:
            render_transfers(report.transfers)
        with right:
            render_risks(report)
        st.divider()
        render_consensus_snapshot(bundle)
        st.divider()
        render_conclusion(report.conclusion)

    with experts_tab:
        render_expert_reveals(report.expert_team_reveals)

    with strategy_tab:
        left, right = st.columns([1.1, 1])
        with left:
            render_chip_strategy(report.chip_strategy)
            st.divider()
            render_disagreements(report.disagreements)
        with right:
            render_fixture_notes(report.fixture_notes)


if __name__ == "__main__":
    main()
