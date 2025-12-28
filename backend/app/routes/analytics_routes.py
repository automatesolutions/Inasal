"""Analytics and behavior tracking routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Optional

from app.auth import get_current_user
from app.behavior_tracker import behavior_tracker

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class TrackInteractionRequest(BaseModel):
    """Request model for tracking interactions"""
    interaction_type: str  # "view_attraction", "click_detail", "save", etc.
    data: Dict = {}  # Additional data about the interaction


@router.post("/track")
async def track_interaction(
    request: TrackInteractionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Track a user interaction for behavior analysis"""
    try:
        success = await behavior_tracker.log_interaction(
            user_id=current_user["user_id"],
            interaction_type=request.interaction_type,
            data=request.data,
        )
        
        if success:
            return {"message": "Interaction tracked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track interaction",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error tracking interaction: {str(e)}",
        )


@router.post("/update-personality")
async def trigger_personality_update(
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger personality update based on behavior"""
    try:
        success = await behavior_tracker.analyze_and_update_personality(
            current_user["user_id"]
        )
        
        if success:
            return {"message": "Personality updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update personality",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating personality: {str(e)}",
        )

