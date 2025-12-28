"""Recommendation API routes"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from app.auth import get_current_user
from app.redis_client import redis_client
from app.strapi_client import strapi_client
from app.make_client import make_client

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


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(
    current_user: dict = Depends(get_current_user),
):
    """Get all recommendations (hotels, restaurants, entertainment, tourist spots)"""
    user_id = current_user["user_id"]
    
    # Try Strapi first (new architecture)
    if strapi_client.api_token:
        try:
            print(f"\n{'='*60}")
            print(f"🔍 DEBUG: Fetching recommendations for user_id: {user_id}")
            print(f"🔍 DEBUG: Strapi URL: {strapi_client.base_url}")
            print(f"🔍 DEBUG: API Token configured: {bool(strapi_client.api_token)}")
            
            recommendations = await strapi_client.get_recommendations(user_id)
            
            print(f"🔍 DEBUG: Recommendations response: {recommendations is not None}")
            
            if recommendations:
                # Strapi v5: Fields are at top level, not in 'attributes'
                # Check if fields are at top level (Strapi v5) or in attributes (Strapi v4)
                if "attributes" in recommendations and recommendations.get("attributes"):
                    attrs = recommendations.get("attributes", {})
                    print(f"🔍 DEBUG: Using Strapi v4 format (fields in attributes)")
                else:
                    # Strapi v5: fields are at top level
                    attrs = recommendations
                    print(f"🔍 DEBUG: Using Strapi v5 format (fields at top level)")
                
                print(f"🔍 DEBUG: Attributes/Fields keys: {list(attrs.keys())}")
                
                # Parse JSON fields (Strapi might return JSON as string)
                # Handle both "restaurants" (plural) and "restaurant" (singular) field names
                restaurants = _parse_json_field(attrs.get("restaurants") or attrs.get("restaurant"))
                hotels = _parse_json_field(attrs.get("hotels"))
                entertainment = _parse_json_field(attrs.get("entertainment"))
                # Handle both "tourist_spots" and "tourists_spots" field names
                tourist_spots = _parse_json_field(attrs.get("tourist_spots") or attrs.get("tourists_spots"))
                secret_recommendations = _parse_json_field(attrs.get("secret_recommendations") or attrs.get("secret_recommendation"))
                
                print(f"🔍 DEBUG: Restaurants count: {len(restaurants)}")
                print(f"🔍 DEBUG: Hotels count: {len(hotels)}")
                print(f"🔍 DEBUG: Entertainment count: {len(entertainment)}")
                print(f"🔍 DEBUG: Tourist spots count: {len(tourist_spots)}")
                
                if restaurants:
                    print(f"🔍 DEBUG: First restaurant: {restaurants[0].get('name', 'N/A')}")
                
                print(f"{'='*60}\n")
                
                return RecommendationsResponse(
                    hotels=hotels,
                    restaurants=restaurants,
                    entertainment=entertainment,
                    tourist_spots=tourist_spots,
                    secret_recommendations=secret_recommendations,
                )
            else:
                print(f"⚠️  WARNING: No recommendations found in Strapi for user_id: {user_id}")
                print(f"{'='*60}\n")
            
            # If no recommendations exist, trigger generation via Make.com
            if make_client.recommendations_webhook:
                await make_client.get_recommendations(user_id)
        except Exception as e:
            # Log the error instead of silently passing
            import traceback
            print(f"\n{'='*60}")
            print(f"❌ ERROR: Failed to fetch from Strapi")
            print(f"Error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            print(f"{'='*60}\n")
            # Fall through to legacy implementation
    
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


@router.get("/test-strapi")
async def test_strapi_direct():
    """Direct test endpoint to see raw Strapi response (no auth required for testing)"""
    import httpx
    
    if not strapi_client.api_token:
        return {"error": "Strapi API token not configured"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Test 1: Get recommendations without populate
            response1 = await client.get(
                f"{strapi_client.base_url}/api/recommendations",
                headers={"Authorization": f"Bearer {strapi_client.api_token}"},
                params={"pagination[limit]": 1},
            )
            data1 = response1.json()
            
            # Test 2: Get recommendations with populate
            response2 = await client.get(
                f"{strapi_client.base_url}/api/recommendations",
                headers={"Authorization": f"Bearer {strapi_client.api_token}"},
                params={"populate": "*", "pagination[limit]": 1},
            )
            data2 = response2.json()
            
            # Test 3: Get specific recommendation by ID
            if data1.get("data"):
                rec_id = data1["data"][0].get("id")
                response3 = await client.get(
                    f"{strapi_client.base_url}/api/recommendations/{rec_id}",
                    headers={"Authorization": f"Bearer {strapi_client.api_token}"},
                    params={"populate": "*"},
                )
                data3 = response3.json()
            else:
                data3 = {"error": "No recommendations found"}
            
            return {
                "test1_no_populate": data1,
                "test2_with_populate": data2,
                "test3_by_id": data3,
            }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.get("/debug")
async def debug_recommendations(
    current_user: dict = Depends(get_current_user),
):
    """Debug endpoint to check Strapi connection and data"""
    user_id = current_user["user_id"]
    
    debug_info = {
        "user_id": user_id,
        "strapi_configured": bool(strapi_client.api_token),
        "strapi_url": strapi_client.base_url,
    }
    
    if not strapi_client.api_token:
        return {
            **debug_info,
            "error": "Strapi API token not configured",
            "fix": "Add STRAPI_API_TOKEN to backend/.env",
        }
    
    try:
        # Get user profile
        profile_id = await strapi_client._get_user_profile_id(user_id)
        debug_info["profile_id"] = profile_id
        
        if not profile_id:
            return {
                **debug_info,
                "error": "User Profile not found in Strapi",
                "fix": "Check if User Profile exists with matching user_id",
            }
        
        # Check all recommendations (not filtered)
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{strapi_client.base_url}/api/recommendations",
                headers={
                    "Authorization": f"Bearer {strapi_client.api_token}",
                },
                params={"pagination[limit]": 100},
            )
            all_recommendations = response.json()
            debug_info["total_recommendations"] = len(all_recommendations.get("data", []))
            
            # Detailed info about each recommendation
            recommendations_list = []
            for r in all_recommendations.get("data", []):
                attrs = r.get("attributes", {})
                user_rel = attrs.get("user", {})
                
                # Extract user ID from relation (handle different formats)
                user_id_from_rel = None
                if isinstance(user_rel, dict):
                    if "data" in user_rel:
                        user_id_from_rel = user_rel["data"].get("id")
                    elif "id" in user_rel:
                        user_id_from_rel = user_rel["id"]
                
                restaurants_data = attrs.get("restaurants") or attrs.get("restaurant")
                restaurants_count = 0
                if isinstance(restaurants_data, list):
                    restaurants_count = len(restaurants_data)
                elif isinstance(restaurants_data, str):
                    try:
                        import json
                        parsed = json.loads(restaurants_data)
                        restaurants_count = len(parsed) if isinstance(parsed, list) else 0
                    except:
                        restaurants_count = 1 if restaurants_data else 0
                
                recommendations_list.append({
                    "id": r.get("id"),
                    "user_id": user_id_from_rel,
                    "published": attrs.get("publishedAt") is not None,
                    "publishedAt": attrs.get("publishedAt"),
                    "has_restaurants": bool(restaurants_data),
                    "restaurants_count": restaurants_count,
                    "restaurants_field_name": "restaurants" if attrs.get("restaurants") else ("restaurant" if attrs.get("restaurant") else None),
                })
            
            debug_info["all_recommendations"] = recommendations_list
        
        # Check filtered recommendations
        filtered_response = await strapi_client.client.get(
            "/api/recommendations",
            params={
                "filters[user][id][$eq]": profile_id,
                "sort": "createdAt:desc",
                "pagination[limit]": 1,
            }
        )
        filtered_data = filtered_response.json()
        debug_info["filtered_recommendations"] = len(filtered_data.get("data", []))
        
        if debug_info["filtered_recommendations"] == 0:
            debug_info["error"] = "No recommendations found for this user"
            debug_info["fix"] = f"Link the Recommendation entry to User Profile ID {profile_id} in Strapi, then Publish it"
            
            # Check if there are any recommendations that aren't linked
            unlinked = [r for r in recommendations_list if r.get("user_id") is None]
            if unlinked:
                debug_info["unlinked_recommendations"] = unlinked
                debug_info["fix"] = f"Found {len(unlinked)} Recommendation entry/entries without User linked. Open Recommendation ID {unlinked[0]['id']} in Strapi and set the User field to User Profile ID {profile_id}, then Publish."
        
        return debug_info
        
    except Exception as e:
        import traceback
        return {
            **debug_info,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.get("/secret")
async def get_secret_recommendations(
    current_user: dict = Depends(get_current_user),
):
    """Get secret recommendations (hidden traits)"""
    user_id = current_user["user_id"]
    
    # Try Strapi first
    if strapi_client.api_token:
        try:
            recommendations = await strapi_client.get_recommendations(user_id)
            if recommendations:
                attrs = recommendations.get("attributes", {})
                secret_recommendations = _parse_json_field(attrs.get("secret_recommendations"))
                return {
                    "secret_recommendations": secret_recommendations,
                }
        except Exception as e:
            import traceback
            print(f"❌ ERROR in get_secret_recommendations: {e}")
            print(traceback.format_exc())
    
    # Fallback to Redis
    cached_data = await redis_client.get(f"recommendations:{user_id}")
    
    if cached_data:
        try:
            data = json.loads(cached_data)
            return {
                "secret_recommendations": data.get("secret_recommendations", []),
            }
        except json.JSONDecodeError:
            pass
    
    return {
        "secret_recommendations": [],
    }
