"""Secret Recommendations API routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.auth import get_current_user
from app.strapi_client import strapi_client
from app.config import settings

router = APIRouter(prefix="/api/secret-recommendations", tags=["secret-recommendations"])


class SecretRecommendationResponse(BaseModel):
    """Response model for secret recommendation"""
    id: Optional[int] = None
    name: str
    url: Optional[str] = None
    description: str
    match_score: Optional[float] = None
    category: Optional[str] = None
    image: Optional[str] = None
    hidden_trait_match: Optional[str] = None
    why_secret: Optional[str] = None
    expires_at: Optional[str] = None


@router.get("")
async def get_secret_recommendations(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Get all secret recommendations for the current user"""
    try:
        user_id = current_user["user_id"]
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching secret recommendations for user_id: {user_id}, limit: {limit}")
        
        recommendations = await strapi_client.get_secret_recommendations(
            user_id=user_id,
            limit=limit
        )
        
        logger.info(f"Received {len(recommendations)} recommendations from Strapi")
        
        # Normalize the response format
        normalized = []
        for rec in recommendations:
            # Handle both Strapi v4 (attributes) and v5 (top-level) formats
            if "attributes" in rec and rec["attributes"]:
                attrs = rec["attributes"]
                rec_id = rec.get("id")
            else:
                attrs = rec
                rec_id = rec.get("id")
            
            # Handle image (can be media object or ID)
            image_data = attrs.get("image")
            image_url = None
            base_url = settings.strapi_url.rstrip("/")
            
            if image_data:
                if isinstance(image_data, dict):
                    # Strapi v5 format: direct object with url field
                    url_path = image_data.get("url")
                    if url_path:
                        # Construct full URL from relative path
                        if not url_path.startswith("http"):
                            # Ensure URL starts with / for proper concatenation
                            if not url_path.startswith("/"):
                                url_path = "/" + url_path
                            image_url = f"{base_url}{url_path}"
                        else:
                            image_url = url_path
                    # Fallback: try nested formats
                    elif "formats" in image_data:
                        formats = image_data.get("formats", {})
                        if "large" in formats and "url" in formats["large"]:
                            url_path = formats["large"]["url"]
                            if not url_path.startswith("http"):
                                if not url_path.startswith("/"):
                                    url_path = "/" + url_path
                                image_url = f"{base_url}{url_path}"
                            else:
                                image_url = url_path
                        elif "medium" in formats and "url" in formats["medium"]:
                            url_path = formats["medium"]["url"]
                            if not url_path.startswith("http"):
                                if not url_path.startswith("/"):
                                    url_path = "/" + url_path
                                image_url = f"{base_url}{url_path}"
                            else:
                                image_url = url_path
                elif isinstance(image_data, str):
                    # If it's a string URL
                    if image_data.startswith("http"):
                        image_url = image_data
                    else:
                        # Relative URL, prepend base URL
                        if not image_data.startswith("/"):
                            image_data = "/" + image_data
                        image_url = f"{base_url}{image_data}"
                elif isinstance(image_data, int):
                    # If it's just an ID, construct URL
                    image_url = f"{base_url}/api/upload/files/{image_data}"
            
            # Handle location component
            location_data = attrs.get("location")
            location = None
            if location_data:
                if isinstance(location_data, dict):
                    location = location_data
                elif isinstance(location_data, list) and len(location_data) > 0:
                    location = location_data[0]
            
            normalized.append({
                "id": rec_id,
                "name": attrs.get("name", ""),
                "url": attrs.get("url"),
                "description": attrs.get("description", ""),
                "match_score": float(attrs.get("match_score", 0)) if attrs.get("match_score") else None,
                "category": attrs.get("category"),
                "image": image_url,
                "hidden_trait_match": attrs.get("hidden_trait_match"),
                "why_secret": attrs.get("why_secret"),
                "expires_at": attrs.get("expires_at"),
                "location": location,
                "tags": attrs.get("tags"),
                "price_range": attrs.get("price_range"),
                "rating": float(attrs.get("rating", 0)) if attrs.get("rating") else None,
                "phone": attrs.get("phone"),
                "address": attrs.get("address"),
                "best_time_to_visit": attrs.get("best_time_to_visit"),
                "featured": attrs.get("featured", False),
                "priority": attrs.get("priority", 0),
                "additional_info": attrs.get("additional_info"),
                    })
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Returning {len(normalized)} normalized recommendations")
        
        return {"data": normalized, "count": len(normalized)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching secret recommendations: {str(e)}"
        )


@router.get("/{recommendation_id}")
async def get_secret_recommendation(
    recommendation_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get a single secret recommendation by ID"""
    try:
        user_id = current_user["user_id"]
        # TEMPORARY: Get all recommendations (no user filtering) for testing
        recommendations = await strapi_client.get_secret_recommendations(
            user_id=user_id,
            limit=100
        )
        
        # Find the specific recommendation
        for rec in recommendations:
            rec_id = rec.get("id")
            if rec_id == recommendation_id:
                # Handle both Strapi v4 (attributes) and v5 (top-level) formats
                if "attributes" in rec and rec["attributes"]:
                    attrs = rec["attributes"]
                else:
                    attrs = rec
                
                # Handle image (can be media object or ID) - same logic as above
                image_data = attrs.get("image")
                image_url = None
                base_url = settings.strapi_url.rstrip("/")
                
                if image_data:
                    if isinstance(image_data, dict):
                        url_path = image_data.get("url")
                        if url_path:
                            if not url_path.startswith("http"):
                                if not url_path.startswith("/"):
                                    url_path = "/" + url_path
                                image_url = f"{base_url}{url_path}"
                            else:
                                image_url = url_path
                        elif "formats" in image_data:
                            formats = image_data.get("formats", {})
                            if "large" in formats and "url" in formats["large"]:
                                url_path = formats["large"]["url"]
                                if not url_path.startswith("http"):
                                    if not url_path.startswith("/"):
                                        url_path = "/" + url_path
                                    image_url = f"{base_url}{url_path}"
                                else:
                                    image_url = url_path
                            elif "medium" in formats and "url" in formats["medium"]:
                                url_path = formats["medium"]["url"]
                                if not url_path.startswith("http"):
                                    if not url_path.startswith("/"):
                                        url_path = "/" + url_path
                                    image_url = f"{base_url}{url_path}"
                                else:
                                    image_url = url_path
                    elif isinstance(image_data, str):
                        if image_data.startswith("http"):
                            image_url = image_data
                        else:
                            if not image_data.startswith("/"):
                                image_data = "/" + image_data
                            image_url = f"{base_url}{image_data}"
                    elif isinstance(image_data, int):
                        image_url = f"{base_url}/api/upload/files/{image_data}"
                
                # Handle location component
                location_data = attrs.get("location")
                location = None
                if location_data:
                    if isinstance(location_data, dict):
                        location = location_data
                    elif isinstance(location_data, list) and len(location_data) > 0:
                        location = location_data[0]
                
                return {
                    "data": {
                        "id": rec_id,
                        "name": attrs.get("name", ""),
                        "url": attrs.get("url"),
                        "description": attrs.get("description", ""),
                        "match_score": float(attrs.get("match_score", 0)) if attrs.get("match_score") else None,
                        "category": attrs.get("category"),
                        "image": image_url,
                        "hidden_trait_match": attrs.get("hidden_trait_match"),
                        "why_secret": attrs.get("why_secret"),
                        "expires_at": attrs.get("expires_at"),
                        "location": location,
                        "tags": attrs.get("tags"),
                        "price_range": attrs.get("price_range"),
                        "rating": float(attrs.get("rating", 0)) if attrs.get("rating") else None,
                        "phone": attrs.get("phone"),
                        "address": attrs.get("address"),
                        "best_time_to_visit": attrs.get("best_time_to_visit"),
                        "featured": attrs.get("featured", False),
                        "priority": attrs.get("priority", 0),
                        "additional_info": attrs.get("additional_info"),
                    }
                }
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret recommendation {recommendation_id} not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching secret recommendation: {str(e)}"
        )

