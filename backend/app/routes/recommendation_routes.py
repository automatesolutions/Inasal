"""Recommendation API routes"""

import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from app.auth import get_current_user
from app.redis_client import redis_client
from app.make_client import make_client
from app.comprehensive_recommendations import ComprehensiveRecommendationsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationItem(BaseModel):
    """Individual recommendation item"""
    name: str
    url: str
    description: str
    match_score: float
    category: Optional[str] = None
    image: Optional[str] = None


class RecommendationsResponse(BaseModel):
    """Response model for recommendations"""
    hotels: List[RecommendationItem]
    restaurants: List[RecommendationItem]
    entertainment: List[RecommendationItem]
    tourist_spots: List[RecommendationItem]
    secret_recommendations: List[dict]  # Can have extra fields


def _parse_json_field(value):
    """Parse JSON field that might be a string or already parsed"""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            print(f"⚠️  WARNING: Failed to parse JSON string: {value[:100]}...")
            return []
    if isinstance(value, list):
        return value
    return []


def _normalize_recommendation_item(item: dict) -> dict:
    """Normalize recommendation item to match frontend expectations
    
    Converts:
    - 'rating' (string/number) → 'match_score' (float 0-1)
    - Unescapes description newlines if needed (\\n → \n)
    - Ensures all required fields are present
    """
    normalized = item.copy()
    
    # Convert rating to match_score if rating exists but match_score doesn't
    if "rating" in normalized and "match_score" not in normalized:
        rating = normalized.get("rating", "0")
        try:
            # Handle both string and numeric ratings
            if isinstance(rating, str):
                rating_float = float(rating)
            else:
                rating_float = float(rating)
            
            # If rating is already 0-1 scale, use as-is; otherwise normalize from 0-10
            if rating_float <= 1.0:
                match_score = rating_float
            else:
                match_score = rating_float / 10.0
            
            # Ensure match_score is between 0 and 1
            match_score = max(0.0, min(1.0, match_score))
            normalized["match_score"] = match_score
        except (ValueError, TypeError):
            normalized["match_score"] = 0.5  # Default if rating is invalid
    
    # Ensure match_score exists (default to 0.5 if missing)
    if "match_score" not in normalized:
        normalized["match_score"] = 0.5
    
    return normalized


def _normalize_recommendation_list(items: list) -> list:
    """Normalize a list of recommendation items"""
    return [_normalize_recommendation_item(item) for item in items]


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(
    current_user: dict = Depends(get_current_user),
):
    """Get all recommendations (hotels, restaurants, entertainment, tourist spots)"""
    user_id = current_user["user_id"]
    
    # Use comprehensive recommendations service
    try:
        service = ComprehensiveRecommendationsService()
        all_recs = await service.get_all_recommendations(user_id)
        
        # Convert to response format
        hotels = all_recs.get("hotels", [])
        restaurants = all_recs.get("restaurants", [])
        tourist_spots = all_recs.get("tourist_spots", [])
        entertainment = all_recs.get("tourist_spots", [])  # Use tourist spots as entertainment
        secret_recommendations = all_recs.get("hidden_gems", [])
        
        return RecommendationsResponse(
            hotels=hotels[:10],
            restaurants=restaurants[:10],
            entertainment=entertainment[:10],
            tourist_spots=tourist_spots[:10],
            secret_recommendations=secret_recommendations[:10],
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        # Fall through to Redis cache
    
    # Fallback to Redis cache (legacy LangGraph workflow)
    cached_data = await redis_client.get(f"recommendations:{user_id}")
    
    if cached_data:
        try:
            data = json.loads(cached_data)
            return RecommendationsResponse(
                hotels=data.get("hotels", []),
                restaurants=data.get("restaurants", []),
                entertainment=data.get("entertainment", []),
                tourist_spots=data.get("tourist_spots", []),
                secret_recommendations=data.get("secret_recommendations", []),
            )
        except json.JSONDecodeError:
            pass
    
    # If not cached, return empty (workflow still running or not configured)
    return RecommendationsResponse(
        hotels=[],
        restaurants=[],
        entertainment=[],
        tourist_spots=[],
        secret_recommendations=[],
    )


@router.get("/secret")
async def get_secret_recommendations(
    current_user: dict = Depends(get_current_user),
):
    """Get secret recommendations (hidden gems)"""
    user_id = current_user["user_id"]
    
    try:
        service = ComprehensiveRecommendationsService()
        all_recs = await service.get_all_recommendations(user_id)
        secret_recommendations = all_recs.get("hidden_gems", [])
        
        return {
            "secret_recommendations": secret_recommendations,
        }
    except Exception as e:
        logger.error(f"Error getting secret recommendations: {e}")
        return {
            "secret_recommendations": [],
        }


class HotelInput(BaseModel):
    """Input model for hotel from Make.com"""
    name: str
    url: str
    description: str
    rating: str  # Rating as string (e.g., "8", "9")
    image: Optional[str] = None


class HotelRecommendationRequest(BaseModel):
    """Request model for hotel recommendations from Make.com"""
    data: dict
    user: Optional[int] = None  # Will be extracted from data.user
    hotels: Optional[List[HotelInput]] = None  # Will be extracted from data.hotels


@router.post("/hotels")
async def receive_hotel_recommendations(
    request: dict,  # Accept raw dict to handle flexible structure
):
    """
    Receive hotel recommendations from Make.com webhook.
    
    Expected format:
    {
        "data": {
            "user": 11,
            "hotels": [
                {
                    "name": "...",
                    "url": "...",
                    "description": "...",
                    "rating": "8",
                    "image": "..."
                }
            ]
        }
    }
    """
    try:
        # Extract user and hotels from the request
        data = request.get("data", {})
        user = data.get("user")
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user ID in request data"
            )
        user_id = str(user)
        hotels_raw = data.get("hotels", [])
        
        if not hotels_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing hotels in request data"
            )
        
        # Transform hotels: convert rating to match_score
        hotels_transformed = []
        for hotel in hotels_raw:
            # Convert rating to match_score (normalize to 0-1 scale)
            rating = hotel.get("rating", "0")
            try:
                # Handle both string and numeric ratings
                if isinstance(rating, str):
                    rating_float = float(rating)
                else:
                    rating_float = float(rating)
                
                # If rating is already 0-1 scale, use as-is; otherwise normalize from 0-10
                if rating_float <= 1.0:
                    match_score = rating_float
                else:
                    match_score = rating_float / 10.0
                
                # Ensure match_score is between 0 and 1
                match_score = max(0.0, min(1.0, match_score))
            except (ValueError, TypeError):
                match_score = 0.5  # Default if rating is invalid
            
            hotels_transformed.append({
                "name": hotel.get("name", ""),
                "url": hotel.get("url", ""),
                "description": hotel.get("description", ""),
                "match_score": match_score,
                "image": hotel.get("image"),
                "rating": str(rating),  # Keep original rating for reference
            })
        
        # Store recommendations in Redis cache
        await redis_client.set(
            f"recommendations:{user_id}",
            json.dumps({
                "hotels": hotels_transformed,
                "updated_at": datetime.utcnow().isoformat()
            }),
            expire=86400  # 24 hours
        )
        
        return {
            "success": True,
            "message": f"Successfully saved {len(hotels_transformed)} hotel recommendations",
            "user_id": user_id,
            "hotels_count": len(hotels_transformed)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error receiving hotel recommendations: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing hotel recommendations: {str(e)}"
        )