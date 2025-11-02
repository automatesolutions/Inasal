"""Recommendation API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional

from fastapi import HTTPException, status

from app.auth import get_current_user
from app.user_profile import UserProfileService

# Conditionally import LangChain-dependent modules
try:
    from app.recommendation import RecommendationEngine, recommendation_engine
    from app.rag_engine import RAGEngine
    rag_engine = RAGEngine()
    HAS_RECOMMENDATIONS = True
except ImportError:
    recommendation_engine = None
    rag_engine = None
    HAS_RECOMMENDATIONS = False

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
profile_service = UserProfileService()
rag_engine = RAGEngine()


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
    if not HAS_RECOMMENDATIONS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not available. LangChain dependencies are not installed.",
        )
    
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

    # Enrich with real-time context (weather, events)
    if rag_engine:
        enriched_recommendations = await rag_engine.enrich_recommendations_with_context(
            recommendations
        )
    else:
        enriched_recommendations = recommendations

    return RecommendationResponse(
        recommendations=enriched_recommendations,
        count=len(enriched_recommendations),
    )


@router.get("/hidden-gems", response_model=RecommendationResponse)
async def get_hidden_gems(
    limit: int = Query(default=5, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
):
    """Get hidden gems for current user"""
    if not HAS_RECOMMENDATIONS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not available. LangChain dependencies are not installed.",
        )
    
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

