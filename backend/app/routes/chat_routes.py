"""Chat API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from app.auth import get_current_user
from app.make_client import make_client
from app.user_profile import UserProfileService
from app.welcome_message_service import WelcomeMessageService
from app.comprehensive_recommendations import ComprehensiveRecommendationsService
from app.user_profile import PersonalityTraits

router = APIRouter(prefix="/api/chat", tags=["chat"])
profile_service = UserProfileService()


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class RichMessage(BaseModel):
    """Rich message with recommendations"""
    type: str
    content: Optional[str] = None
    recommendations: Optional[Dict[str, List[Dict]]] = None
    personality_summary: Optional[str] = None


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
                return ChatResponse(response=make_response["response"])
        except Exception as e:
            # Fall through to legacy implementation if Make.com fails
            pass
    
    # Fallback to legacy LangChain implementation
    try:
        from app.chat_agent import ChatAgent
        chat_agent = ChatAgent()
        response = await chat_agent.chat(chat_message.message, user_id)
        
        return ChatResponse(response=response)
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please configure Make.com webhook or install LangChain dependencies.",
        )


@router.get("/welcome", response_model=RichMessage)
async def get_welcome_message(
    current_user: dict = Depends(get_current_user)
):
    """
    Get MOGI's welcome message with all recommendations
    Called automatically when user first enters chat
    """
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = current_user["user_id"]
    
    # Get user profile - this will check cache if BigQuery has defaults
    profile = await profile_service.get_profile(user_id)
    
    if not profile:
        logger.warning(f"No profile found for user {user_id}")
        personality = PersonalityTraits()  # Use default 0.5 for all traits
        user_name = "friend"
    else:
        personality = profile.personality
        user_name = profile.name if profile.name else "friend"
        
        personality_dict = personality.model_dump()
        logger.info(f"📋 Using personality for {user_id}: {personality_dict}")
    
    # Generate welcome message - the LLM will intelligently use personality if available
    welcome_service = WelcomeMessageService()
    welcome_text = await welcome_service.generate_welcome_message(
        user_name, personality
    )
    
    # Get personality summary
    personality_summary = welcome_service.format_personality_summary(personality)
    
    logger.info(f"✅ Welcome message generated: {welcome_text[:100]}...")
    logger.info(f"✅ Personality summary: {personality_summary}")
    
    # Get all recommendations
    try:
        recommendations_service = ComprehensiveRecommendationsService()
        recommendations = await recommendations_service.get_all_recommendations(
            user_id
        )
        logger.info(f"Generated recommendations for {user_id}: {sum(len(v) for v in recommendations.values())} total items")
    except Exception as e:
        logger.error(f"Error getting recommendations for {user_id}: {e}", exc_info=True)
        # Return empty recommendations on error
        recommendations = {
            "hotels": [],
            "restaurants": [],
            "accommodations": [],
            "tourist_spots": [],
            "beaches": [],
            "mountains": [],
            "resorts": [],
            "places_to_avoid": [],
            "businesses": [],
            "events": [],
            "hidden_gems": []
        }
    
    return RichMessage(
        type="welcome",
        content=welcome_text,
        recommendations=recommendations,
        personality_summary=personality_summary
    )

