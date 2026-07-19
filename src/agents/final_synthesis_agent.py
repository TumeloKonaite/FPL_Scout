from __future__ import annotations

import json
from pathlib import Path

from agents import Agent, Runner

from src.agents.model_factory import build_openai_model, close_openai_model
from src.schemas.final_report import AggregatedFPLReport, FinalGameweekReport


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_PROMPT_PATH = PROMPTS_DIR / "final_synthesizer.txt"


def load_prompt(prompt_path: Path | None = None) -> str:
    """Load the final synthesis prompt from disk."""
    path = prompt_path or DEFAULT_PROMPT_PATH

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return path.read_text(encoding="utf-8").strip()


def build_final_synthesis_agent(prompt_path: Path | None = None) -> Agent:
    """Build and return the final synthesis agent."""
    instructions = load_prompt(prompt_path)

    return Agent(
        name="FPL Final Synthesizer",
        instructions=instructions,
        output_type=FinalGameweekReport,
        model=build_openai_model(),
    )


def format_aggregated_report_input(report: AggregatedFPLReport) -> str:
    """Convert aggregated structured data into a deterministic prompt payload."""
    payload = report.model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True)


async def run_final_synthesis(report: AggregatedFPLReport) -> FinalGameweekReport:
    """Run the final synthesis agent against aggregated report data."""
    agent = build_final_synthesis_agent()
    input_text = format_aggregated_report_input(report)

    try:
        result = await Runner.run(
            agent,
            input=f"Aggregated FPL report:\n\n{input_text}",
        )
    finally:
        await close_openai_model(agent.model)

    if not isinstance(result.final_output, FinalGameweekReport):
        raise TypeError("Agent did not return FinalGameweekReport")

    return result.final_output
