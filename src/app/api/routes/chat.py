from __future__ import annotations

from fastapi import APIRouter, Depends

from src.app.api.schemas.chat import ChatRequest, ChatResponse
from src.app.core.config import Settings
from src.app.core.dependencies import get_app_settings

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _settings: Settings = Depends(get_app_settings),
) -> ChatResponse:
    return ChatResponse(response=request.message, session_id=request.session_id)
