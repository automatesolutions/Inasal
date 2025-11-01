"""Recommendation API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional

from app.auth import get_current_user
from app.user_profile import UserProfileService
from app.recommendation import RecommendationEngine, recommendation_engine

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
profile_service = UserProfileService()


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""
    recommendations: List[dict]
    count: int


@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    limit: int = Query(default=10, ge=1, le=20),
    query: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Get personalized recommendations for current user"""
    # Get user profile
    profile = await profile_service.get_profile(current_user["user_id"])
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    # Ensure recommendation engine is initialized
    if not recommendation_engine.vector_store:
        await recommendation_engine.initialize()

    # Get recommendations
    recommendations = await recommendation_engine.get_recommendations(
        profile, query=query, limit=limit
    )

    return RecommendationResponse(
        recommendations=recommendations,
        count=len(recommendations),
    )


@router.get("/hidden-gems", response_model=RecommendationResponse)
async def get_hidden_gems(
    limit: int = Query(default=5, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
):
    """Get hidden gems for current user"""
    profile = await profile_service.get_profile(current_user["user_id"])
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    if not recommendation_engine.vector_store:
        await recommendation_engine.initialize()

    hidden_gems = await recommendation_engine.get_hidden_gems(profile, limit=limit)

    return RecommendationResponse(
        recommendations=hidden_gems,
        count=len(hidden_gems),
    )

