from __future__ import annotations

from pathlib import Path

from agents import Agent, AgentOutputSchema

from src.agents.model_factory import build_openai_model
from src.schemas.expert_analysis import ExpertVideoAnalysis


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_PROMPT_PATH = PROMPTS_DIR / "expert_video_analyst.txt"


def load_prompt(prompt_path: Path | None = None) -> str:
    """Load the expert video analyst prompt from disk."""
    path = prompt_path or DEFAULT_PROMPT_PATH

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return path.read_text(encoding="utf-8").strip()


def build_expert_video_agent(prompt_path: Path | None = None) -> Agent:
    """Build and return the expert video analysis agent."""
    instructions = load_prompt(prompt_path)

    return Agent(
        name="FPL Video Analyst",
        instructions=instructions,
        # player_positions is intentionally keyed by arbitrary player names. JSON
        # Schema represents that mapping with additionalProperties, which the
        # Agents SDK's strict schema mode rejects before a model call is made.
        output_type=AgentOutputSchema(
            ExpertVideoAnalysis,
            strict_json_schema=False,
        ),
        model=build_openai_model(),
    )
