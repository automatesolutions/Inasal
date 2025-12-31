"""Strapi API client for content management"""

import httpx
from typing import Optional, Dict, List, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StrapiClient:
    """Client for interacting with Strapi CMS API"""

    def __init__(self):
        self.base_url = settings.strapi_url.rstrip("/")
        self.api_token = settings.strapi_api_token
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_token}" if self.api_token else "",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def _get_user_profile_id(self, user_id: str) -> Optional[int]:
        """Get Strapi user profile ID by user_id"""
        try:
            response = await self.client.get(
                "/api/user-profiles",
                params={"filters[user_id][$eq]": user_id}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error getting user profile ID for {user_id}: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id"""
        try:
            response = await self.client.get(
                "/api/user-profiles",
                params={"filters[user_id][$eq]": user_id}
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0] if data.get("data") else None
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None

    async def create_user_profile(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        personality: Optional[Dict] = None,
        preferences: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user profile in Strapi"""
        try:
            payload = {
                "data": {
                    "user_id": user_id,
                    "email": email,
                }
            }
            if name:
                payload["data"]["name"] = name
            if personality:
                payload["data"]["personality"] = personality
            if preferences:
                payload["data"]["preferences"] = preferences

            response = await self.client.post(
                "/api/user-profiles",
                json=payload
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error creating user profile for {email}: {e}")
            return None

    async def update_user_profile(
        self,
        user_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update user profile"""
        profile_id = await self._get_user_profile_id(user_id)
        if not profile_id:
            return None

        try:
            payload = {"data": updates}
            response = await self.client.put(
                f"/api/user-profiles/{profile_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error updating user profile for {user_id}: {e}")
            return None

    async def get_attractions(
        self,
        limit: int = 100,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Get all attractions from Strapi"""
        try:
            params = {"pagination[limit]": limit}
            if filters:
                # Add filters to params
                for key, value in filters.items():
                    params[f"filters[{key}]"] = value

            response = await self.client.get(
                "/api/attractions",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Error getting attractions: {e}")
            return []

    async def create_interaction_log(
        self,
        user_id: str,
        interaction_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create interaction log in Strapi"""
        profile_id = await self._get_user_profile_id(user_id)
        if not profile_id:
            logger.warning(f"User profile not found for {user_id}, skipping interaction log")
            return None

        try:
            payload = {
                "data": {
                    "user": profile_id,
                    "interaction_type": interaction_type,
                    "content": content,
                }
            }
            if metadata:
                payload["data"]["metadata"] = metadata

            response = await self.client.post(
                "/api/interaction-logs",
                json=payload
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error creating interaction log: {e}")
            return None

    async def get_recommendations(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user recommendations from Strapi
        
        TEMPORARY: Currently returns ALL published recommendations for testing
        TODO: Re-enable user filtering after testing
        """
        print(f"🔍 DEBUG: User ID: {user_id}")
        print(f"⚠️  TEMP MODE: Bypassing user filtering - showing ALL recommendations")
        
        try:
            # TEMPORARY: Get ALL published recommendations (no user filtering)
            url = "/api/recommendations"
            params = {
                "populate": "*",  # Populate all relations and fields
                "sort": "createdAt:desc",
                "pagination[limit]": 10,  # Get first 10
            }
            
            print(f"🔍 DEBUG: Request URL: {url}")
            print(f"🔍 DEBUG: Request params: {params}")
            
            response = await self.client.get(url, params=params)
            
            print(f"🔍 DEBUG: Response status: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            print(f"🔍 DEBUG: Response data keys: {list(data.keys())}")
            print(f"🔍 DEBUG: Total recommendations found: {len(data.get('data', []))}")
            
            recommendations = data.get("data", [])
            
            if not recommendations:
                print(f"⚠️  WARNING: No recommendations found in Strapi")
                print(f"   → Check if Recommendation entries exist and are Published")
                return None
            
            # Get the first published recommendation
            result = recommendations[0]
            rec_id = result.get('id')
            print(f"🔍 DEBUG: Using recommendation ID: {rec_id}")
            
            # Debug: Print full structure
            print(f"🔍 DEBUG: Full recommendation structure:")
            print(f"   - ID: {rec_id}")
            print(f"   - Keys: {list(result.keys())}")
            
            # Strapi v5: Fields are at top level, not in 'attributes'
            # Check if fields are at top level (Strapi v5) or in attributes (Strapi v4)
            if 'attributes' in result and result['attributes']:
                attrs = result.get('attributes', {})
                print(f"🔍 DEBUG: Using Strapi v4 format (fields in attributes)")
            else:
                # Strapi v5: fields are at top level
                attrs = result
                print(f"🔍 DEBUG: Using Strapi v5 format (fields at top level)")
            
            print(f"🔍 DEBUG: Available fields: {list(attrs.keys())}")
            
            # Check all possible field names for restaurants (both v4 and v5 formats)
            restaurants = (
                attrs.get('restaurants') or 
                attrs.get('restaurant') or
                attrs.get('Restaurants') or
                attrs.get('Restaurant')
            )
            
            print(f"🔍 DEBUG: Checking restaurant field...")
            print(f"   - restaurants: {attrs.get('restaurants')}")
            print(f"   - restaurant: {attrs.get('restaurant')}")
            
            if restaurants:
                print(f"✅ DEBUG: Found restaurants field!")
                print(f"🔍 DEBUG: Restaurants type: {type(restaurants)}")
                print(f"🔍 DEBUG: Restaurants value (first 200 chars): {str(restaurants)[:200]}")
                
                if isinstance(restaurants, str):
                    print(f"🔍 DEBUG: Restaurants is JSON string (will be parsed)")
                    try:
                        import json
                        restaurants = json.loads(restaurants)
                        print(f"🔍 DEBUG: Parsed restaurants: {restaurants}")
                    except Exception as e:
                        print(f"⚠️  ERROR parsing restaurants JSON: {e}")
                        restaurants = None
                elif isinstance(restaurants, list):
                    print(f"🔍 DEBUG: Restaurants is array with {len(restaurants)} items")
                    if restaurants:
                        print(f"🔍 DEBUG: First restaurant: {restaurants[0]}")
            else:
                print(f"⚠️  WARNING: No restaurants field found!")
                print(f"   → Available fields: {list(attrs.keys())}")
                print(f"   → Check field name in Strapi (should be 'restaurants' or 'restaurant')")
            
            # Return result with normalized structure for v5 compatibility
            # Wrap in attributes if needed for downstream code
            if 'attributes' not in result or not result.get('attributes'):
                # Convert v5 format to v4-like format for compatibility
                normalized = {
                    'id': result.get('id'),
                    'documentId': result.get('documentId'),
                    'attributes': {
                        'restaurants': restaurants or attrs.get('restaurants') or attrs.get('restaurant'),
                        'hotels': attrs.get('hotels'),
                        'entertainment': attrs.get('entertainment'),
                        'tourist_spots': attrs.get('tourist_spots') or attrs.get('tourists_spots'),
                        'secret_recommendations': attrs.get('secret_recommendations') or attrs.get('secret_recommendation'),
                    }
                }
                return normalized
            
            return result
        except Exception as e:
            import traceback
            logger.error(f"Error getting recommendations for {user_id}: {e}")
            print(f"\n❌ ERROR in get_recommendations:")
            print(f"Error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}\n")
            return None

    async def create_recommendations(
        self,
        user_id: str,
        hotels: List[Dict],
        restaurants: List[Dict],
        entertainment: List[Dict],
        tourist_spots: List[Dict],
        secret_recommendations: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create recommendations in Strapi"""
        profile_id = await self._get_user_profile_id(user_id)
        if not profile_id:
            return None

        try:
            payload = {
                "data": {
                    "user": profile_id,
                    "hotels": hotels,
                    "restaurants": restaurants,
                    "entertainment": entertainment,
                    "tourist_spots": tourist_spots,
                }
            }
            if secret_recommendations:
                payload["data"]["secret_recommendations"] = secret_recommendations

            response = await self.client.post(
                "/api/recommendations",
                json=payload
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error creating recommendations for {user_id}: {e}")
            return None

    async def update_recommendations(
        self,
        user_id: str,
        hotels: Optional[List[Dict]] = None,
        restaurants: Optional[List[Dict]] = None,
        entertainment: Optional[List[Dict]] = None,
        tourist_spots: Optional[List[Dict]] = None,
        secret_recommendations: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update existing recommendations in Strapi (partial update)"""
        profile_id = await self._get_user_profile_id(user_id)
        if not profile_id:
            return None

        try:
            # First, get existing recommendations
            response = await self.client.get(
                "/api/recommendations",
                params={
                    "filters[user][id][$eq]": profile_id,
                    "sort": "createdAt:desc",
                    "pagination[limit]": 1,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("data"):
                # No existing recommendations, create new one
                return await self.create_recommendations(
                    user_id=user_id,
                    hotels=hotels or [],
                    restaurants=restaurants or [],
                    entertainment=entertainment or [],
                    tourist_spots=tourist_spots or [],
                    secret_recommendations=secret_recommendations
                )
            
            # Get the most recent recommendation
            rec_id = data["data"][0]["id"]
            
            # Build update payload with only provided fields
            payload = {"data": {}}
            if hotels is not None:
                payload["data"]["hotels"] = hotels
            if restaurants is not None:
                payload["data"]["restaurants"] = restaurants
            if entertainment is not None:
                payload["data"]["entertainment"] = entertainment
            if tourist_spots is not None:
                payload["data"]["tourist_spots"] = tourist_spots
            if secret_recommendations is not None:
                payload["data"]["secret_recommendations"] = secret_recommendations

            response = await self.client.put(
                f"/api/recommendations/{rec_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"Error updating recommendations for {user_id}: {e}")
            return None

    async def get_secret_recommendations(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get secret recommendations for a user from the separate Secret Recommendations collection
        
        TEMPORARY: Currently returns ALL published secret recommendations for testing
        TODO: Re-enable user filtering after testing
        """
        # TEMPORARY: Get ALL published secret recommendations (no user filtering)
        # profile_id = await self._get_user_profile_id(user_id)
        # if not profile_id:
        #     logger.warning(f"User profile not found for {user_id}")
        #     return []

        try:
            params = {
                # TEMPORARY: Removed user filter for testing
                # "filters[user][id][$eq]": profile_id,
                "populate": "*",  # Populate all fields including image
                "sort": "createdAt:desc",
                "pagination[limit]": limit,
            }

            logger.info(f"Fetching secret recommendations with params: {params}")
            response = await self.client.get(
                "/api/secret-recommendations",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            recommendations = data.get("data", [])
            logger.info(f"Successfully fetched {len(recommendations)} secret recommendations")
            return recommendations
        except Exception as e:
            logger.error(f"Error getting secret recommendations for {user_id}: {e}")
            # Log the full error details for debugging
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"Strapi error response: {error_body}")
                except:
                    logger.error(f"Strapi error response text: {e.response.text}")
            return []

    async def create_secret_recommendation(
        self,
        user_id: str,
        name: str,
        description: str,
        url: Optional[str] = None,
        match_score: Optional[float] = None,
        category: Optional[str] = None,
        image: Optional[int] = None,
        hidden_trait_match: Optional[str] = None,
        why_secret: Optional[str] = None,
        expires_at: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        price_range: Optional[str] = None,
        rating: Optional[float] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        best_time_to_visit: Optional[str] = None,
        featured: Optional[bool] = None,
        priority: Optional[int] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        published: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create a new secret recommendation"""
        profile_id = await self._get_user_profile_id(user_id)
        if not profile_id:
            return None

        try:
            payload = {
                "data": {
                    "user": profile_id,
                    "name": name,
                    "description": description,
                }
            }

            if url:
                payload["data"]["url"] = url
            if match_score is not None:
                payload["data"]["match_score"] = match_score
            if category:
                payload["data"]["category"] = category
            if image is not None:
                payload["data"]["image"] = image  # Media ID
            if hidden_trait_match:
                payload["data"]["hidden_trait_match"] = hidden_trait_match
            if why_secret:
                payload["data"]["why_secret"] = why_secret
            if expires_at:
                payload["data"]["expires_at"] = expires_at
            if location:
                payload["data"]["location"] = location
            if tags is not None:
                payload["data"]["tags"] = tags
            if price_range:
                payload["data"]["price_range"] = price_range
            if rating is not None:
                payload["data"]["rating"] = rating
            if phone:
                payload["data"]["phone"] = phone
            if address:
                payload["data"]["address"] = address
            if best_time_to_visit:
                payload["data"]["best_time_to_visit"] = best_time_to_visit
            if featured is not None:
                payload["data"]["featured"] = featured
            if priority is not None:
                payload["data"]["priority"] = priority
            if additional_info:
                payload["data"]["additional_info"] = additional_info
            if published:
                from datetime import datetime
                payload["data"]["publishedAt"] = datetime.utcnow().isoformat() + "Z"

            response = await self.client.post(
                "/api/secret-recommendations",
                json=payload
            )
            response.raise_for_status()
            return response.json().get("data")
        except Exception as e:
            logger.error(f"Error creating secret recommendation: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
strapi_client = StrapiClient()

