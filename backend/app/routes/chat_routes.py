"""Chat API routes"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.chat_agent import ChatAgent

router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_agent = ChatAgent()


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
async def chat(
    chat_message: ChatMessage, current_user: dict = Depends(get_current_user)
):
    """Send a chat message and get AI response"""
    if not HAS_CHAT_AGENT or not chat_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. LangChain dependencies are not installed.",
        )
    response = await chat_agent.chat(chat_message.message, current_user["user_id"])
    return ChatResponse(response=response)

