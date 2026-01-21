"""User profile API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.user_profile import (
    UserProfileService,
    UserProfile,
    PersonalityTraits,
    UserPreferences,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])
profile_service = UserProfileService()


class ProfileResponse(BaseModel):
    """Profile response model"""
    profile: UserProfile


class UpdatePersonalityRequest(BaseModel):
    """Request model for updating personality"""
    personality: PersonalityTraits


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating preferences"""
    preferences: UserPreferences


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    profile = await profile_service.get_profile(current_user["user_id"])
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return ProfileResponse(profile=profile)


@router.put("/me/personality", response_model=ProfileResponse)
async def update_personality(
    request: UpdatePersonalityRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user personality traits"""
    profile = await profile_service.update_personality(
        current_user["user_id"], request.personality
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    
    return ProfileResponse(profile=profile)


@router.put("/me/preferences", response_model=ProfileResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user preferences"""
    profile = await profile_service.update_preferences(
        current_user["user_id"], request.preferences
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    
    return ProfileResponse(profile=profile)


@router.get("/me/interactions")
async def get_my_interactions(
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """Get user interaction history"""
    interactions = await profile_service.get_interaction_history(
        current_user["user_id"], limit=limit
    )
    return {"interactions": interactions}

