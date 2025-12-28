"""Chat API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user
from app.make_client import make_client
from app.strapi_client import strapi_client

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
async def chat(
    chat_message: ChatMessage, current_user: dict = Depends(get_current_user)
):
    """Send a chat message and get AI response via Make.com workflow"""
    user_id = current_user["user_id"]
    
    # Try Make.com workflow first (new architecture)
    if make_client.chat_webhook:
        try:
            make_response = await make_client.send_chat_message(
                user_id,
                chat_message.message
            )
            
            if make_response and "response" in make_response:
                # Log interaction in Strapi
                await strapi_client.create_interaction_log(
                    user_id,
                    "chat",
                    {
                        "message": chat_message.message,
                        "response": make_response["response"]
                    }
                )
                return ChatResponse(response=make_response["response"])
        except Exception as e:
            # Fall through to legacy implementation if Make.com fails
            pass
    
    # Fallback to legacy LangChain implementation
    try:
        from app.chat_agent import ChatAgent
        chat_agent = ChatAgent()
        response = await chat_agent.chat(chat_message.message, user_id)
        
        # Log interaction in Strapi if available
        await strapi_client.create_interaction_log(
            user_id,
            "chat",
            {
                "message": chat_message.message,
                "response": response
            }
        )
        
        return ChatResponse(response=response)
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please configure Make.com webhook or install LangChain dependencies.",
        )

