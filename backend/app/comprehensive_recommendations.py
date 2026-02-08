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
        """Calculate personality match score for an item (0-1). Uses personality_match when present; otherwise infers from type/tags."""
        # Use personality_match field when available
        if "personality_match" in item and isinstance(item["personality_match"], dict):
            pm = item["personality_match"]
            # Only average over traits that are present in the item (so 3 traits don't get diluted by 6)
            traits = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
            total = 0.0
            count = 0
            for t in traits:
                item_val = pm.get(t)
                if item_val is not None:
                    user_val = getattr(personality, t, 0.5)
                    total += user_val * item_val
                    count += 1
            if count > 0:
                # Weighted average: high user trait + high item trait = high score (0-1)
                score = total / count
                return min(1.0, max(0.0, score))
            return 0.5
        
        # Infer match from type/tags when personality_match missing
        item_type = (item.get("type") or "").lower()
        tags = item.get("tags", []) or []
        tags_lower = [t.lower() if isinstance(t, str) else str(t).lower() for t in tags]
        
        type_to_traits = {
            "historical": ("history_buff", "cultural"),
            "cultural": ("cultural", "history_buff"),
            "food": ("foodie", "social"),
            "nature": ("nature_lover", "adventurous"),
            "entertainment": ("social", "adventurous"),
            "religious": ("cultural", "history_buff"),
            "shopping": ("foodie", "cultural"),
            "hotel": ("social", "cultural"),
        }
        trait_scores = []
        for t, (a, b) in type_to_traits.items():
            if t in item_type or any(t in tag for tag in tags_lower):
                trait_scores.append(getattr(personality, a, 0.5))
                trait_scores.append(getattr(personality, b, 0.5))
        if trait_scores:
            return min(1.0, 0.4 + (sum(trait_scores) / len(trait_scores)) * 0.5)  # 0.4-0.9 range
        return 0.5

    def _format_recommendation(self, item: Dict, match_score: float) -> Dict:
        """Format a recommendation item with links and precise directions"""
        import urllib.parse
        
        location = item.get("location", {})
        if isinstance(location, list) and len(location) > 0:
            location = location[0]
        
        lat = location.get("latitude") if isinstance(location, dict) else None
        lng = location.get("longitude") if isinstance(location, dict) else None
        address = item.get("address") or (location.get("address") if isinstance(location, dict) else None)
        place_name = item.get("name", "Bacolod attraction")
        
        links = {}
        
        # View Details: use official website if available, else Google search (avoids 404 from non-existent /recommendations/id page)
        if item.get("url"):
            links["website"] = item["url"]
            links["details"] = item["url"]  # "View Details" opens official site
        else:
            # Fallback: Google search for place name + Bacolod so user can find info
            search_query = urllib.parse.quote(f"{place_name} Bacolod Philippines")
            links["details"] = f"https://www.google.com/search?q={search_query}"
        
        # Map and directions: use correct Google Maps URLs
        if lat is not None and lng is not None:
            dest = f"{lat},{lng}"
            links["map"] = f"https://www.google.com/maps?q={dest}"
            links["directions"] = f"https://www.google.com/maps/dir/?api=1&destination={dest}"
        elif address:
            encoded = urllib.parse.quote(address)
            links["map"] = f"https://www.google.com/maps/search/?api=1&query={encoded}"
            links["directions"] = f"https://www.google.com/maps/dir/?api=1&destination={encoded}"
        else:
            # Fallback: search by place name + Bacolod for correct location
            query = urllib.parse.quote(f"{place_name}, Bacolod, Philippines")
            links["map"] = f"https://www.google.com/maps/search/?api=1&query={query}"
            links["directions"] = f"https://www.google.com/maps/dir/?api=1&destination={query}"
        
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
        
        formatted = {
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
        
        # Add address if available
        if address:
            formatted["address"] = address
        
        return formatted

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
                "secret_spots": []
            }
        
        personality = profile.personality
        
        # Initialize recommendation engine
        await self.initialize()
        
        # Get main categories first
        tourist_spots = await self._get_tourist_spots(profile, user_location)
        hotels = await self._get_hotels(profile, user_location)
        restaurants = await self._get_restaurants(profile, user_location)
        beaches = await self._get_beaches(profile, user_location)
        mountains = await self._get_mountains(profile, user_location)
        resorts = await self._get_resorts(profile, user_location)
        
        # Collect all recommended place names to avoid duplicates in secret spots
        already_recommended_names = set()
        for cat_list in [tourist_spots, hotels, restaurants, beaches, mountains, resorts]:
            for item in cat_list:
                name = item.get("name", "").lower().strip()
                if name:
                    already_recommended_names.add(name)
        
        recommendations = {
            "tourist_spots": tourist_spots,
            "hotels": hotels,
            "restaurants": restaurants,
            "beaches": beaches,
            "mountains": mountains,
            "resorts": resorts,
            "accommodations": await self._get_accommodations(profile, user_location),
            "places_to_avoid": await self._get_scams_and_danger_zones(user_location),
            "businesses": await self._get_businesses(user_location),
            "events": await self._get_events(user_location),
            "secret_spots": await self._get_secret_spots(profile, user_location, already_recommended_names)
        }
        
        # Save all recommendations to InstantDB
        try:
            await self._save_recommendations_to_instantdb(user_id, recommendations)
        except Exception as e:
            logger.error(f"Error saving recommendations to InstantDB: {e}")
        
        return recommendations

    async def _get_hotels(self, profile, location) -> List[Dict]:
        """Get hotel recommendations (personality-correlated)"""
        try:
            # Use recommendation engine - request more to get hotel types
            recs = await self.recommendation_engine.get_recommendations(profile, limit=15)
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

    async def _get_scams_and_danger_zones(self, location) -> List[Dict]:
        """Get scams and danger zones in Bacolod"""
        # Bacolod-specific scams and danger zones
        scams_and_dangers = [
            {
                "id": "scam_001",
                "name": "Fake Tour Packages",
                "description": "Beware of unauthorized tour operators offering suspiciously cheap packages. Always book through licensed travel agencies or verified online platforms.",
                "type": "scam",
                "area": "Tourist areas, malls, and transportation hubs",
                "advice": "Verify tour operator credentials, check reviews, and avoid paying upfront for suspiciously low prices.",
                "official_link": "https://www.tourism.gov.ph",
                "location": {
                    "latitude": 10.6769,
                    "longitude": 122.9503,
                    "address": "Bacolod City, Negros Occidental"
                }
            },
            {
                "id": "danger_001",
                "name": "Pickpocket Hotspots",
                "description": "Be cautious in crowded areas, especially during festivals (MassKara Festival) and in public markets. Keep valuables secure and avoid displaying expensive items.",
                "type": "danger_zone",
                "area": "Downtown Bacolod, Public Markets, Festival Grounds",
                "advice": "Use anti-theft bags, keep wallets in front pockets, avoid carrying large amounts of cash, and stay alert in crowded places.",
                "official_link": "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6769,
                    "longitude": 122.9503,
                    "address": "Downtown Bacolod"
                }
            },
            {
                "id": "scam_002",
                "name": "Overpriced Taxi/Jeepney Rides",
                "description": "Some drivers may charge tourists higher rates. Always ask for the meter or agree on a price before starting the trip.",
                "type": "scam",
                "area": "Airport, Bus Terminals, Tourist Spots",
                "advice": "Use ride-hailing apps (Grab) when possible, or negotiate prices upfront. Know approximate distances and typical fares.",
                "official_link": "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6769,
                    "longitude": 122.9503,
                    "address": "Bacolod Transportation Hubs"
                }
            },
            {
                "id": "danger_002",
                "name": "Unsafe Areas at Night",
                "description": "Some areas in Bacolod are less safe after dark. Avoid walking alone in poorly lit areas, especially away from main tourist zones.",
                "type": "danger_zone",
                "area": "Outskirts, Industrial Areas, Some Barangays",
                "advice": "Use transportation at night, stay in well-lit areas, travel in groups when possible, and inform your accommodation of your plans.",
                "official_link": "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6769,
                    "longitude": 122.9503,
                    "address": "Bacolod City Outskirts"
                }
            }
        ]
        
        formatted = []
        for item in scams_and_dangers:
            formatted_item = self._format_recommendation(item, 0.0)  # No match score for safety info
            formatted_item["type"] = item.get("type")
            formatted_item["area"] = item.get("area")
            formatted_item["advice"] = item.get("advice")
            if item.get("official_link"):
                formatted_item["links"]["official"] = item["official_link"]
            formatted.append(formatted_item)
        
        return formatted

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

    async def _get_secret_spots(self, profile, location, already_recommended_names: Optional[set] = None) -> List[Dict]:
        """Get secret spots - unique, profile-based recommendations (1-2 items max)"""
        try:
            if already_recommended_names is None:
                already_recommended_names = set()
            
            # Get all recommendations to avoid duplicates
            all_recs = await self.recommendation_engine.get_recommendations(profile, limit=30)
            
            # Filter for unique, offbeat places with high personality match
            # Prefer places with lower popularity but high match score
            secret_candidates = []
            for item in all_recs:
                # Skip if already recommended in other categories
                item_name = item.get("name", "").lower().strip()
                if item_name in already_recommended_names:
                    continue
                
                match_score = self._calculate_match_score(item, profile.personality)
                # Include high-match items; prefer offbeat when available
                item_type = item.get("type", "").lower()
                tags = item.get("tags", [])
                tags_lower = [t.lower() if isinstance(t, str) else str(t).lower() for t in tags]
                
                is_offbeat = (
                    "hidden" in item.get("name", "").lower() or
                    "secret" in item.get("name", "").lower() or
                    "lesser-known" in item.get("description", "").lower() or
                    "offbeat" in tags_lower or
                    ("local" in tags_lower and "favorite" in item.get("description", "").lower()) or
                    (item_type in ["cultural", "historical", "food"] and match_score > 0.7)
                )
                
                # Accept if offbeat and match >= 0.6, or any item with match >= 0.75
                if (is_offbeat and match_score >= 0.6) or match_score >= 0.75:
                    secret_candidates.append((item, match_score))
            
            # If no offbeat/high-match found, take top 2 by match score from remaining
            if not secret_candidates:
                all_with_scores = [
                    (item, self._calculate_match_score(item, profile.personality))
                    for item in all_recs if item.get("name", "").lower().strip() not in already_recommended_names
                ]
                all_with_scores.sort(key=lambda x: x[1], reverse=True)
                secret_candidates = all_with_scores[:2]
            
            secret_candidates.sort(key=lambda x: x[1], reverse=True)
            secret_items = [item for item, score in secret_candidates[:2]]
            
            formatted = []
            for item in secret_items:
                match_score = self._calculate_match_score(item, profile.personality)
                formatted_item = self._format_recommendation(item, match_score)
                
                # Add secret spot specific fields
                formatted_item["why_secret"] = item.get("why_secret", 
                    "A unique spot perfectly matched to your personality - discovered just for you!")
                formatted_item["hidden_trait_match"] = item.get("hidden_trait_match", "personalized_match")
                
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
                        category="secret_spots",
                        match_score=match_score,
                        personality_match_scores=personality_match_scores,
                        recommendation_data=formatted_item
                    )
                except Exception as e:
                    logger.error(f"Error saving recommendation score: {e}")
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting secret spots: {e}")
            return []
    
    async def _save_recommendations_to_instantdb(self, user_id: str, recommendations: Dict[str, List[Dict]]) -> bool:
        """Save all recommendations to InstantDB for the user"""
        try:
            from app.instantdb_client import instantdb_client
            
            if not instantdb_client._is_available():
                logger.debug("InstantDB not available, skipping recommendation save")
                return False
            
            # Prepare recommendations data
            recommendations_data = {
                "user_id": user_id,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            # Save to InstantDB using transact
            headers = instantdb_client._get_headers()
            url = f"{instantdb_client.base_url}/admin/transact"
            
            # Use update to create or update recommendations
            payload = {
                "steps": [
                    ["update", "user_recommendations", user_id, recommendations_data]
                ]
            }
            
            response = await instantdb_client.client.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Saved recommendations to InstantDB for user: {user_id}")
                logger.debug(f"   Categories: {list(recommendations.keys())}")
                logger.debug(f"   Total items: {sum(len(v) for v in recommendations.values())}")
                return True
            else:
                logger.warning(f"⚠️  Failed to save recommendations to InstantDB: {response.status_code} - {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving recommendations to InstantDB: {e}")
            import traceback
            logger.debug(f"   Traceback: {traceback.format_exc()}")
            return False
