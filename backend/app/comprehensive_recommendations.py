"""Comprehensive recommendations service for all categories"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.user_profile import UserProfile, UserProfileService
from app.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)
profile_service = UserProfileService()


class ComprehensiveRecommendationsService:
    """Fetch recommendations for all categories"""

    def __init__(self):
        self.recommendation_engine = RecommendationEngine()

    async def initialize(self):
        """Initialize recommendation engine"""
        await self.recommendation_engine.initialize()

    def _calculate_match_score(self, item: Dict, personality) -> float:
        """Calculate personality match score for an item"""
        # Use personality_match field if available
        if "personality_match" in item and isinstance(item["personality_match"], dict):
            pm = item["personality_match"]
            score = (
                personality.adventurous * pm.get("adventurous", 0.5) +
                personality.cultural * pm.get("cultural", 0.5) +
                personality.foodie * pm.get("foodie", 0.5) +
                personality.nature_lover * pm.get("nature_lover", 0.5) +
                personality.history_buff * pm.get("history_buff", 0.5) +
                personality.social * pm.get("social", 0.5)
            ) / 6.0
            return min(score, 1.0)
        return 0.5  # Default match score

    def _format_recommendation(self, item: Dict, match_score: float) -> Dict:
        """Format a recommendation item with links"""
        location = item.get("location", {})
        if isinstance(location, list) and len(location) > 0:
            location = location[0]
        
        lat = location.get("latitude") if isinstance(location, dict) else None
        lng = location.get("longitude") if isinstance(location, dict) else None
        
        links = {}
        if item.get("id"):
            links["details"] = f"/recommendations/{item['id']}"
        if item.get("url"):
            links["website"] = item["url"]
        if lat and lng:
            links["map"] = f"https://maps.google.com/?q={lat},{lng}"
        if item.get("booking_link"):
            links["booking"] = item["booking_link"]
        
        # Handle image URL (could be string, dict, or nested Strapi format)
        image_url = None
        if item.get("image"):
            if isinstance(item["image"], str):
                image_url = item["image"]
            elif isinstance(item["image"], dict):
                # Strapi format: image.data.attributes.url
                if "data" in item["image"]:
                    data = item["image"]["data"]
                    if isinstance(data, dict) and "attributes" in data:
                        image_url = data["attributes"].get("url")
                    elif isinstance(data, list) and len(data) > 0:
                        image_url = data[0].get("attributes", {}).get("url")
                elif "url" in item["image"]:
                    image_url = item["image"]["url"]
        elif item.get("images"):
            images = item["images"]
            if isinstance(images, list) and len(images) > 0:
                img = images[0]
                if isinstance(img, str):
                    image_url = img
                elif isinstance(img, dict):
                    image_url = img.get("url") or img.get("data", {}).get("attributes", {}).get("url")
        
        # Ensure image URL is absolute
        if image_url and not image_url.startswith("http"):
            # If relative URL, assume it's from public folder or CDN
            # Frontend should handle relative URLs
            pass
        
        return {
            "id": str(item.get("id", "")),
            "name": item.get("name", "Unknown"),
            "description": item.get("description", ""),
            "match_score": match_score,
            "links": links,
            "location": location if isinstance(location, dict) else {},
            "image": image_url,
            "rating": item.get("rating"),
            "price_range": item.get("price_range"),
        }

    async def get_all_recommendations(
        self,
        user_id: str,
        user_location: Optional[Dict[str, float]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get recommendations for all categories
        """
        # Load user profile
        profile = await profile_service.get_profile(user_id)
        if not profile:
            # Return empty recommendations if no profile
            return {
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
        
        personality = profile.personality
        
        # Initialize recommendation engine
        await self.initialize()
        
        recommendations = {
            "hotels": await self._get_hotels(profile, user_location),
            "restaurants": await self._get_restaurants(profile, user_location),
            "accommodations": await self._get_accommodations(profile, user_location),
            "tourist_spots": await self._get_tourist_spots(profile, user_location),
            "beaches": await self._get_beaches(profile, user_location),
            "mountains": await self._get_mountains(profile, user_location),
            "resorts": await self._get_resorts(profile, user_location),
            "places_to_avoid": await self._get_places_to_avoid(user_location),
            "businesses": await self._get_businesses(user_location),
            "events": await self._get_events(user_location),
            "hidden_gems": await self._get_hidden_gems(profile, user_location)
        }
        
        return recommendations

    async def _get_hotels(self, profile, location) -> List[Dict]:
        """Get hotel recommendations"""
        try:
            # Use recommendation engine
            recs = await self.recommendation_engine.get_recommendations(profile, limit=5)
            hotels = [r for r in recs if r.get("type") == "hotel" or "hotel" in r.get("name", "").lower()]
            
            formatted_hotels = []
            for item in hotels[:5]:
                match_score = self._calculate_match_score(item, profile.personality)
                formatted_item = self._format_recommendation(item, match_score)
                formatted_hotels.append(formatted_item)
                
                # Save recommendation score to BigQuery
                try:
                    from app.bigquery_client import bigquery_client
                    personality_match_scores = {
                        "adventurous": profile.personality.adventurous * item.get("personality_match", {}).get("adventurous", 0.5),
                        "cultural": profile.personality.cultural * item.get("personality_match", {}).get("cultural", 0.5),
                        "foodie": profile.personality.foodie * item.get("personality_match", {}).get("foodie", 0.5),
                        "nature_lover": profile.personality.nature_lover * item.get("personality_match", {}).get("nature_lover", 0.5),
                        "history_buff": profile.personality.history_buff * item.get("personality_match", {}).get("history_buff", 0.5),
                        "social": profile.personality.social * item.get("personality_match", {}).get("social", 0.5),
                    }
                    await bigquery_client.save_recommendation_score(
                        user_id=profile.user_id,
                        item_id=str(item.get("id", "")),
                        item_name=item.get("name", "Unknown"),
                        category="hotels",
                        match_score=match_score,
                        personality_match_scores=personality_match_scores,
                        recommendation_data=formatted_item
                    )
                except Exception as e:
                    logger.error(f"Error saving recommendation score: {e}")
            
            return formatted_hotels
        except Exception as e:
            logger.error(f"Error getting hotels: {e}")
            return []

    async def _get_restaurants(self, profile, location) -> List[Dict]:
        """Get restaurant recommendations"""
        try:
            recs = await self.recommendation_engine.get_recommendations(profile, limit=10)
            restaurants = [r for r in recs if r.get("type") == "food" or "restaurant" in r.get("name", "").lower()]
            
            formatted_restaurants = []
            for item in restaurants[:7]:
                match_score = self._calculate_match_score(item, profile.personality)
                formatted_item = self._format_recommendation(item, match_score)
                formatted_restaurants.append(formatted_item)
                
                # Save recommendation score to BigQuery
                try:
                    from app.bigquery_client import bigquery_client
                    personality_match_scores = {
                        "adventurous": profile.personality.adventurous * item.get("personality_match", {}).get("adventurous", 0.5),
                        "cultural": profile.personality.cultural * item.get("personality_match", {}).get("cultural", 0.5),
                        "foodie": profile.personality.foodie * item.get("personality_match", {}).get("foodie", 0.5),
                        "nature_lover": profile.personality.nature_lover * item.get("personality_match", {}).get("nature_lover", 0.5),
                        "history_buff": profile.personality.history_buff * item.get("personality_match", {}).get("history_buff", 0.5),
                        "social": profile.personality.social * item.get("personality_match", {}).get("social", 0.5),
                    }
                    await bigquery_client.save_recommendation_score(
                        user_id=profile.user_id,
                        item_id=str(item.get("id", "")),
                        item_name=item.get("name", "Unknown"),
                        category="restaurants",
                        match_score=match_score,
                        personality_match_scores=personality_match_scores,
                        recommendation_data=formatted_item
                    )
                except Exception as e:
                    logger.error(f"Error saving recommendation score: {e}")
            
            return formatted_restaurants
        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []

    async def _get_accommodations(self, profile, location) -> List[Dict]:
        """Get accommodation recommendations (same as hotels for now)"""
        return await self._get_hotels(profile, location)

    async def _get_tourist_spots(self, profile, location) -> List[Dict]:
        """Get tourist spot recommendations"""
        try:
            recs = await self.recommendation_engine.get_recommendations(profile, limit=10)
            spots = [r for r in recs if r.get("type") in ["historical", "cultural", "nature", "entertainment"]]
            
            return [
                self._format_recommendation(
                    item,
                    self._calculate_match_score(item, profile.personality)
                )
                for item in spots[:7]
            ]
        except Exception as e:
            logger.error(f"Error getting tourist spots: {e}")
            return []

    async def _get_beaches(self, profile, location) -> List[Dict]:
        """Get beach recommendations"""
        try:
            recs = await self.recommendation_engine.get_recommendations(profile, limit=10)
            beaches = [r for r in recs if "beach" in r.get("name", "").lower() or "beach" in r.get("tags", [])]
            
            return [
                self._format_recommendation(
                    item,
                    self._calculate_match_score(item, profile.personality)
                )
                for item in beaches[:5]
            ]
        except Exception as e:
            logger.error(f"Error getting beaches: {e}")
            return []

    async def _get_mountains(self, profile, location) -> List[Dict]:
        """Get mountain/hiking recommendations"""
        try:
            recs = await self.recommendation_engine.get_recommendations(profile, limit=10)
            mountains = [r for r in recs if "mountain" in r.get("name", "").lower() or "hiking" in r.get("tags", [])]
            
            return [
                self._format_recommendation(
                    item,
                    self._calculate_match_score(item, profile.personality)
                )
                for item in mountains[:5]
            ]
        except Exception as e:
            logger.error(f"Error getting mountains: {e}")
            return []

    async def _get_resorts(self, profile, location) -> List[Dict]:
        """Get resort recommendations"""
        try:
            recs = await self.recommendation_engine.get_recommendations(profile, limit=10)
            resorts = [r for r in recs if "resort" in r.get("name", "").lower()]
            
            return [
                self._format_recommendation(
                    item,
                    self._calculate_match_score(item, profile.personality)
                )
                for item in resorts[:5]
            ]
        except Exception as e:
            logger.error(f"Error getting resorts: {e}")
            return []

    async def _get_places_to_avoid(self, location) -> List[Dict]:
        """Get dangerous areas or places to avoid"""
        # This would come from Strapi place-to-avoid content type
        # For now, return empty list
        return []

    async def _get_businesses(self, location) -> List[Dict]:
        """Get nearby businesses and companies"""
        # This would come from Strapi business content type
        # For now, return empty list
        return []

    async def _get_events(self, location) -> List[Dict]:
        """Get upcoming events nearby"""
        # This would come from Strapi event content type
        # For now, return empty list
        return []

    async def _get_hidden_gems(self, profile, location) -> List[Dict]:
        """Get hidden gems recommendations"""
        try:
            # Use existing get_hidden_gems method
            hidden_gems = await self.recommendation_engine.get_hidden_gems(profile, limit=5)
            
            # Format hidden gems
            all_gems = hidden_gems
            
            formatted = []
            for item in all_gems[:5]:
                match_score = self._calculate_match_score(item, profile.personality)
                formatted_item = self._format_recommendation(item, match_score)
                
                # Add hidden gem specific fields
                formatted_item["why_secret"] = item.get("why_secret", "A lesser-known local favorite")
                formatted_item["hidden_trait_match"] = item.get("hidden_trait_match", "offbeat_explorer")
                
                formatted.append(formatted_item)
                
                # Save recommendation score to BigQuery
                try:
                    from app.bigquery_client import bigquery_client
                    personality_match_scores = {
                        "adventurous": profile.personality.adventurous * item.get("personality_match", {}).get("adventurous", 0.5),
                        "cultural": profile.personality.cultural * item.get("personality_match", {}).get("cultural", 0.5),
                        "foodie": profile.personality.foodie * item.get("personality_match", {}).get("foodie", 0.5),
                        "nature_lover": profile.personality.nature_lover * item.get("personality_match", {}).get("nature_lover", 0.5),
                        "history_buff": profile.personality.history_buff * item.get("personality_match", {}).get("history_buff", 0.5),
                        "social": profile.personality.social * item.get("personality_match", {}).get("social", 0.5),
                    }
                    await bigquery_client.save_recommendation_score(
                        user_id=profile.user_id,
                        item_id=str(item.get("id", "")),
                        item_name=item.get("name", "Unknown"),
                        category="hidden_gems",
                        match_score=match_score,
                        personality_match_scores=personality_match_scores,
                        recommendation_data=formatted_item
                    )
                except Exception as e:
                    logger.error(f"Error saving recommendation score: {e}")
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting hidden gems: {e}")
            return []
