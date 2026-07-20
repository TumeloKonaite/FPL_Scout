from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

from agents import AgentOutputSchema, ModelResponse
from agents.models.interface import Model, ModelTracing
from openai.types.responses.response_prompt_param import ResponsePromptParam

from src.agents.expert_video_agent import build_expert_video_agent
from src.agents.final_synthesis_agent import build_final_synthesis_agent
from src.schemas.expert_analysis import ExpertVideoAnalysis


class FakeModel(Model):
    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list,
        model_settings,
        tools: list,
        output_schema,
        handoffs: list,
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> ModelResponse:
        raise NotImplementedError

    async def stream_response(
        self,
        system_instructions: str | None,
        input: str | list,
        model_settings,
        tools: list,
        output_schema,
        handoffs: list,
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> AsyncIterator:
        raise NotImplementedError


def test_build_expert_video_agent_uses_shared_model_factory(tmp_path: Path) -> None:
    prompt_path = tmp_path / "expert_prompt.txt"
    prompt_path.write_text("Expert instructions", encoding="utf-8")
    fake_model = FakeModel()

    with patch(
        "src.agents.expert_video_agent.build_openai_model",
        return_value=fake_model,
    ) as mock_factory:
        agent = build_expert_video_agent(prompt_path)

    assert agent.model is fake_model
    assert isinstance(agent.output_type, AgentOutputSchema)
    assert agent.output_type.is_strict_json_schema() is False
    assert agent.output_type.output_type is ExpertVideoAnalysis
    mock_factory.assert_called_once_with()


def test_build_final_synthesis_agent_uses_shared_model_factory(tmp_path: Path) -> None:
    prompt_path = tmp_path / "final_prompt.txt"
    prompt_path.write_text("Final instructions", encoding="utf-8")
    fake_model = FakeModel()

    with patch(
        "src.agents.final_synthesis_agent.build_openai_model",
        return_value=fake_model,
    ) as mock_factory:
        agent = build_final_synthesis_agent(prompt_path)

    assert agent.model is fake_model
    mock_factory.assert_called_once_with()
