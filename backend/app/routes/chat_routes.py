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


@router.get("/debug/personality-cache/{user_id}")
async def debug_personality_cache(user_id: str):
    """Debug endpoint to check cached personality"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Direct access to cache
    from app.user_profile import _personality_cache, _cache_lock
    
    with _cache_lock:
        cached = _personality_cache.get(user_id)
        cache_size = len(_personality_cache)
    
    profile = await profile_service.get_profile(user_id)
    
    logger.info(f"🔍 Cache debug for {user_id}:")
    logger.info(f"   Cached personality: {cached.model_dump() if cached else 'None'}")
    logger.info(f"   Cache size: {cache_size}")
    logger.info(f"   Profile from DB: {profile.personality.model_dump() if profile else 'None'}")
    
    return {
        "user_id": user_id,
        "cached_personality": cached.model_dump() if cached else None,
        "db_personality": profile.personality.model_dump() if profile else None,
        "cache_size": cache_size,
        "all_cached_users": list(_personality_cache.keys())
    }



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
    import asyncio
    logger = logging.getLogger(__name__)
    
    user_id = current_user["user_id"]
    logger.info(f"🎯 Welcome endpoint called for user {user_id}")
    
    # Wait for personality analysis to complete and cache to be populated
    # Personality analysis runs in background, so we need to wait for it
    personality = None
    for attempt in range(60):  # Wait up to 30 seconds (60 * 0.5s)
        profile = await profile_service.get_profile(user_id)
        if profile:
            personality_dict = profile.personality.model_dump()
            # Check if personality has meaningful traits (any > 0.5)
            has_traits = any(v > 0.5 for v in personality_dict.values())
            
            if has_traits:
                logger.info(f"✅ Got personality with traits on attempt {attempt}: {personality_dict}")
                personality = profile.personality
                break
            else:
                if attempt == 0 or attempt % 10 == 0:  # Log every 10 attempts
                    logger.info(f"⏳ Waiting for personality analysis... (attempt {attempt+1}/60, traits: {personality_dict})")
                await asyncio.sleep(0.5)
        else:
            logger.warning(f"⚠️ Profile not found on attempt {attempt}")
            await asyncio.sleep(0.5)
    
    # If no personality found after waiting, get whatever is available
    if personality is None:
        logger.warning(f"⚠️ No personality found after 30s wait for {user_id}")
        profile = await profile_service.get_profile(user_id)
        if profile:
            personality = profile.personality
        else:
            personality = PersonalityTraits()  # Use defaults
    
    # Get user name
    profile = await profile_service.get_profile(user_id)
    user_name = profile.name if profile and profile.name else "friend"
    
    personality_dict = personality.model_dump()
    logger.info(f"📋 Final personality for {user_id}: {personality_dict}")
    
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

