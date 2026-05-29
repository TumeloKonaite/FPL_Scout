from __future__ import annotations

from fastapi import APIRouter

from src.app.api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(response=request.message, session_id=request.session_id)
