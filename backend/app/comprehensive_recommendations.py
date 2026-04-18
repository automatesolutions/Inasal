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

    async def _get_curated_details_fallbacks(self) -> Dict[str, str]:
        """Load curated URLs from InstantDB (Google Sheet). Returns category_key -> first URL for View Details fallback."""
        try:
            from app.instantdb_client import instantdb_client
            if not instantdb_client._is_available():
                return {}
            all_ = await instantdb_client.get_all_curated_resources()
            fallbacks = {}
            # Map sheet categories to our recommendation categories
            for slug, doc in all_.items():
                urls = doc.get("urls") or []
                if urls:
                    fallbacks[slug] = urls[0]
            return fallbacks
        except Exception as e:
            logger.debug(f"Curated fallbacks not available: {e}")
            return {}
    
    async def _get_scraped_content_for_category(self, category: str) -> List[Dict[str, Any]]:
        """Load scraped content from InstantDB for a category."""
        try:
            from app.instantdb_client import instantdb_client
            if not instantdb_client._is_available():
                logger.warning(f"InstantDB not available, cannot load scraped content for {category}")
                return []
            scraped = await instantdb_client.get_scraped_content_by_category(category)
            logger.info(f"Loaded {len(scraped)} scraped content items for category: {category}")
            if scraped:
                logger.debug(f"Sample scraped item for {category}: {scraped[0].get('title', 'N/A')[:100]}")
            return scraped
        except Exception as e:
            logger.warning(f"Scraped content not available for {category}: {e}", exc_info=True)
            return []
    
    def _enhance_with_scraped_content(
        self, 
        item: Dict, 
        scraped_content: List[Dict[str, Any]],
        user_location: Optional[Dict[str, float]] = None,
        personality: Optional[Any] = None
    ) -> Dict:
        """
        Enhance a recommendation item with scraped content.
        Uses location proximity, event dates, and personality alignment for better matching.
        """
        item_name_lower = (item.get("name") or "").lower()
        best_match = None
        best_score = 0.0
        
        # Calculate match scores for each scraped content item
        for scraped in scraped_content:
            score = 0.0
            
            # 1. Name/text similarity (base score) - more flexible matching
            scraped_title = (scraped.get("title") or "").lower()
            scraped_text = (scraped.get("content_text") or "").lower()
            scraped_desc = (scraped.get("description") or "").lower()
            places = [p.lower() for p in scraped.get("places_mentioned", [])]
            
            # Extract key words from item name (remove common words)
            item_words = [w for w in item_name_lower.split() if len(w) > 3 and w not in ["the", "and", "hotel", "resort"]]
            
            # Check if key words from item name appear in scraped content
            name_match = False
            if item_words:
                # Check if at least 2 key words match (for multi-word names)
                matches = sum(1 for word in item_words if word in scraped_title or word in scraped_text or word in scraped_desc)
                if matches >= min(2, len(item_words)) or (len(item_words) == 1 and matches == 1):
                    name_match = True
            else:
                # Fallback: exact substring match
                name_match = (
                    item_name_lower in scraped_title
                    or item_name_lower in scraped_text
                    or item_name_lower in scraped_desc
                    or any(item_name_lower in p or p in item_name_lower for p in places)
                )
            
            if name_match:
                score += 0.4  # Base match score
            
            # 2. Location proximity (if user location provided)
            if user_location and scraped.get("location"):
                scraped_loc = scraped["location"]
                if isinstance(scraped_loc, dict):
                    scraped_lat = scraped_loc.get("latitude")
                    scraped_lng = scraped_loc.get("longitude")
                    if scraped_lat is not None and scraped_lng is not None:
                        try:
                            import math
                            user_lat = user_location.get("latitude")
                            user_lng = user_location.get("longitude")
                            if user_lat is not None and user_lng is not None:
                                # Calculate distance (Haversine)
                                R = 6371.0  # Earth radius in km
                                dlat = math.radians(float(scraped_lat) - float(user_lat))
                                dlon = math.radians(float(scraped_lng) - float(user_lng))
                                a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(float(user_lat))) * math.cos(math.radians(float(scraped_lat))) * math.sin(dlon / 2) ** 2
                                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                                distance_km = R * c
                                
                                # Score based on proximity (closer = higher score)
                                if distance_km < 5:
                                    score += 0.3
                                elif distance_km < 10:
                                    score += 0.2
                                elif distance_km < 20:
                                    score += 0.1
                        except (ValueError, TypeError):
                            pass
            
            # 3. Personality alignment (if personality provided)
            if personality and scraped.get("personality_keywords"):
                item_keywords = scraped["personality_keywords"]
                if isinstance(item_keywords, dict):
                    personality_traits = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
                    trait_matches = 0
                    trait_score_sum = 0.0
                    
                    for trait in personality_traits:
                        user_trait_score = getattr(personality, trait, 0.5)
                        item_trait_score = item_keywords.get(trait, 0.0)
                        
                        if isinstance(item_trait_score, (int, float)) and item_trait_score > 0:
                            # Score based on alignment (both high = good match)
                            alignment = 1.0 - abs(user_trait_score - item_trait_score)
                            trait_score_sum += alignment * user_trait_score
                            trait_matches += 1
                    
                    if trait_matches > 0:
                        personality_score = trait_score_sum / trait_matches
                        score += personality_score * 0.4  # Increased weight (40%) for personality match
            
            # 4. Use scraped location if item doesn't have precise coordinates
            if scraped.get("location") and isinstance(scraped["location"], dict):
                scraped_loc = scraped["location"]
                item_loc = item.get("location", {})
                if isinstance(item_loc, dict):
                    # Use scraped coordinates if item doesn't have them
                    if not item_loc.get("latitude") and scraped_loc.get("latitude"):
                        if not item.get("location"):
                            item["location"] = {}
                        item["location"]["latitude"] = scraped_loc["latitude"]
                        item["location"]["longitude"] = scraped_loc["longitude"]
                        if scraped_loc.get("address"):
                            item["location"]["address"] = scraped_loc["address"]
                        score += 0.1  # Bonus for providing location data
            
            # Track best match
            if score > best_score:
                best_score = score
                best_match = scraped
        
        # Enhance item with best matching scraped content
        if best_match:
            logger.debug(f"Enhancing item '{item.get('name')}' with scraped content (match score: {best_score:.2f})")
            # Enhance with scraped content
            if not item.get("image") and best_match.get("images"):
                item["image"] = best_match["images"][0]
                logger.debug(f"  Added image from scraped content")
            if not item.get("description") and best_match.get("description"):
                item["description"] = best_match["description"][:500]
                logger.debug(f"  Added description from scraped content")
            if best_match.get("url") and not item.get("url"):
                item["url"] = best_match["url"]
                logger.debug(f"  Added URL from scraped content")
            
            # Add events if available
            if best_match.get("events") and not item.get("events"):
                item["events"] = best_match["events"]
                logger.debug(f"  Added {len(best_match['events'])} events from scraped content")
            
            # CRITICAL: Add personality_keywords from scraped content for automatic personality matching
            if best_match.get("personality_keywords"):
                item["personality_keywords"] = best_match["personality_keywords"]
                logger.debug(f"  Added personality_keywords from scraped content: {best_match['personality_keywords']}")
            
            # Store match score for debugging
            item["_scraped_content_match_score"] = round(best_score, 2)
        else:
            logger.debug(f"No scraped content match found for item '{item.get('name')}' (checked {len(scraped_content)} items)")
        
        return item

    def _calculate_match_score(self, item: Dict, personality) -> float:
        """Calculate personality match score for an item (0-1). Uses personality_keywords from scraped content."""
        # Priority 1: Use personality_keywords from scraped content (most accurate)
        if "personality_keywords" in item and isinstance(item["personality_keywords"], dict):
            pk = item["personality_keywords"]
            traits = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
            total = 0.0
            count = 0
            for t in traits:
                item_val = pk.get(t)
                if item_val is not None and isinstance(item_val, (int, float)):
                    user_val = getattr(personality, t, 0.5)
                    # Enhanced scoring: considers both magnitude and similarity
                    # High user trait + high item trait = strong match
                    # Similar values = better alignment
                    magnitude_match = user_val * item_val  # Both high = high score
                    similarity = 1.0 - abs(user_val - item_val)  # Closer values = better
                    # Combined score: 70% magnitude, 30% similarity
                    combined_score = magnitude_match * 0.7 + similarity * 0.3
                    total += combined_score
                    count += 1
            if count > 0:
                score = total / count
                # Convert to percentage (0-1 range) and ensure reasonable minimum
                # Scale to 0.1-1.0 range for better visibility (0% = 0.1, 100% = 1.0)
                scaled_score = 0.1 + (score * 0.9)  # Maps 0-1 to 0.1-1.0
                return min(1.0, max(0.1, scaled_score))
        
        # Priority 2: Use personality_match field when available
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
        
        # Priority 3: Infer match from type/tags when personality data missing
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

    def _format_recommendation(
        self,
        item: Dict,
        match_score: float,
        details_fallback_url: Optional[str] = None,
        hide_source_link: bool = False,
    ) -> Dict:
        """Format a recommendation item with links and precise directions.
        details_fallback_url: from InstantDB curated resources (Google Sheet) when item has no url.
        hide_source_link: if True, do not add website/details links (only map and directions).
        """
        import urllib.parse
        
        location = item.get("location", {})
        if isinstance(location, list) and len(location) > 0:
            location = location[0]
        
        lat = location.get("latitude") if isinstance(location, dict) else None
        lng = location.get("longitude") if isinstance(location, dict) else None
        address = item.get("address") or (location.get("address") if isinstance(location, dict) else None)
        place_name = item.get("name", "Bacolod attraction")
        
        links = {}
        
        # View Details / Website: only set if not hide_source_link (e.g. tourist spots: don't show content link)
        if not hide_source_link:
            if item.get("url"):
                links["website"] = item["url"]
                links["details"] = item["url"]
            elif details_fallback_url:
                links["website"] = details_fallback_url
                links["details"] = details_fallback_url
            else:
                search_query = urllib.parse.quote(f"{place_name} Bacolod Philippines")
                links["details"] = f"https://www.google.com/search?q={search_query}"
        else:
            # Only search link for "View Details", no website
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
        
        # Ensure rating is a number if present
        rating = item.get("rating")
        if rating is not None:
            try:
                rating = float(rating) if isinstance(rating, (int, float, str)) else None
            except (ValueError, TypeError):
                rating = None
        
        formatted = {
            "id": str(item.get("id", "")),
            "name": item.get("name", "Unknown"),
            "description": item.get("description", ""),
            "match_score": round(match_score, 2),  # Round to 2 decimal places (0.00-1.00)
            "match_percentage": int(match_score * 100),  # Also provide as percentage (0-100) for frontend
            "links": links,
            "location": location if isinstance(location, dict) else {},
            "image": image_url,
            "rating": rating,  # Now guaranteed to be a number or None
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
        
        # Load curated URLs from InstantDB (Google Sheet sync) for View Details fallback
        curated_details = await self._get_curated_details_fallbacks()
        
        # NOTE: We're now using InstantDB scraped content DIRECTLY, not JSON
        # The recommendation engine is no longer used for primary data
        
        # Get main categories first
        tourist_spots = await self._get_tourist_spots(profile, user_location, curated_details)
        hotels = await self._get_hotels(profile, user_location, curated_details)
        restaurants = await self._get_restaurants(profile, user_location, curated_details)
        beaches = await self._get_beaches(profile, user_location, curated_details)
        mountains = await self._get_mountains(profile, user_location, curated_details)
        resorts = await self._get_resorts(profile, user_location, curated_details)
        
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
            "accommodations": await self._get_accommodations(profile, user_location, curated_details),
            "places_to_avoid": await self._get_scams_and_danger_zones(user_location, curated_details),
            "businesses": await self._get_businesses(user_location),
            "events": await self._get_events(user_location),
            "secret_spots": await self._get_secret_spots(profile, user_location, already_recommended_names, curated_details)
        }
        
        # Save all recommendations to InstantDB
        try:
            await self._save_recommendations_to_instantdb(user_id, recommendations)
        except Exception as e:
            logger.error(f"Error saving recommendations to InstantDB: {e}")
        
        return recommendations

    def _is_general_article_or_guide(self, name: str, description: str = "") -> bool:
        """Return True if name/description looks like a general article, guide, or blog post (not a specific place)."""
        name_lower = str(name).lower()
        desc_lower = str(description).lower()
        text = f"{name_lower} {desc_lower}"
        
        # Article/blog indicators
        article_keywords = [
            "tourist spots", "things to do", "places to visit", "travel guide", "complete guide",
            "hidden gems", "best places", "top 10", "top 5", "must visit", "must-see",
            "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "january",
            "2024", "2025", "2026", "2027",
            "blog", "article", "post", "guide to", "how to", "where to",
            "visit -", "beyond to visit", "and beyond", "city and beyond",
        ]
        
        # Check if it's clearly an article/blog title
        if any(kw in text for kw in article_keywords):
            return True
        
        # Check if name is too long (articles often have long descriptive titles)
        if len(name) > 80:
            return True
        
        # Check if name contains date patterns (e.g., "February 8, 2026")
        import re
        if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}', name_lower):
            return True
        
        return False

    async def _get_hotels(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get hotel recommendations from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("accommodation_hotels")
            
            if not scraped_content:
                logger.warning("No scraped content found for accommodation_hotels in InstantDB")
                return []
            
            # 1) Only specific places: require hotel_name (entity), skip raw page/content records
            # 2) Exclude general articles/guides/blog posts
            # 3) Deduplicate by normalized place name
            # 4) Only include match_score > 50%
            # 5) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown hotel", "unknown"}
            formatted_hotels = []
            
            for item in scraped_content:
                hotel_name = item.get("hotel_name") or item.get("name") or item.get("title")
                description = item.get("description", "")
                
                # Skip page-level records (no specific hotel name)
                if not hotel_name or str(hotel_name).strip() in ("", "Unknown Hotel", "Unknown"):
                    continue
                
                # CRITICAL: Skip general articles/guides/blog posts FIRST (filter out website link content)
                # This catches items like "17 Tourist Spots in Bacolod City and Beyond to Visit..."
                if self._is_general_article_or_guide(hotel_name, description):
                    logger.info(f"🚫 Skipping general article/guide from hotels: {hotel_name[:80]}...")
                    continue
                
                # Skip test/placeholder hotels
                if str(hotel_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                
                # CRITICAL: Only include items that have hotel_name field (specific entity extraction)
                # Items without hotel_name are likely page-level records, not specific hotels
                if not item.get("hotel_name"):
                    # If no hotel_name field, be VERY strict - must look like a specific hotel name
                    name_lower = str(hotel_name).lower()
                    # Must contain hotel/accommodation keywords AND be reasonably short
                    has_hotel_keyword = any(kw in name_lower for kw in ["hotel", "resort", "inn", "lodge", "villa", "apartment", "hostel", "guesthouse", "accommodation", "suite", "palace", "tower", "plaza", "manor", "bed", "stay"])
                    is_short_specific = len(name_lower) <= 60  # Shorter threshold for non-hotel_name items
                    # Must NOT contain article/blog keywords
                    has_article_keywords = any(kw in name_lower for kw in ["tourist", "spots", "guide", "visit", "beyond", "hidden gems", "things to do", "places to", "best places", "top 10", "must visit"])
                    
                    if not has_hotel_keyword or not is_short_specific or has_article_keywords:
                        logger.info(f"🚫 Skipping non-hotel item (no hotel_name field): {hotel_name[:80]}...")
                        continue
                
                # Skip if it's just a URL or generic title
                raw_url = item.get("url", "")
                if raw_url and hotel_name and (raw_url[:50] in str(hotel_name) or len(str(hotel_name)) < 3):
                    continue
                
                # Deduplicate: normalize name (lower, strip, collapse spaces)
                name_key = " ".join(str(hotel_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": hotel_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                    "rating": item.get("rating"),
                    "price_range": item.get("price_range"),
                    "amenities": item.get("amenities", []),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                formatted_item = self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                )
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

    async def _get_restaurants(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get restaurant recommendations from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("restaurants_food")
            
            if not scraped_content:
                logger.warning("No scraped content found for restaurants_food in InstantDB")
                return []
            
            # 1) Only specific places: require restaurant_name (entity), skip raw page/content records
            # 2) Deduplicate by normalized place name
            # 3) Only include match_score > 50%
            # 4) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown restaurant", "unknown"}
            formatted_restaurants = []
            
            for item in scraped_content:
                restaurant_name = item.get("restaurant_name") or item.get("name") or item.get("title")
                # Skip page-level records (no specific restaurant name)
                if not restaurant_name or str(restaurant_name).strip() in ("", "Unknown Restaurant", "Unknown"):
                    continue
                # Skip test/placeholder restaurants
                if str(restaurant_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                # Skip if it's just a URL or generic title
                raw_url = item.get("url", "")
                if raw_url and restaurant_name and (raw_url[:50] in str(restaurant_name) or len(str(restaurant_name)) < 3):
                    continue
                
                # Deduplicate: normalize name (lower, strip, collapse spaces)
                name_key = " ".join(str(restaurant_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": restaurant_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                    "cuisine_type": item.get("cuisine_type"),
                    "specialties": item.get("specialties", []),
                    "opening_hours": item.get("opening_hours"),
                    "rating": item.get("rating"),
                    "price_range": item.get("price_range"),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                formatted_item = self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                )
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

    async def _get_accommodations(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get accommodation recommendations (same as hotels for now)"""
        return await self._get_hotels(profile, location, curated_details)

    def _is_restaurant_or_food_place(self, item: Dict) -> bool:
        """Return True if item is a restaurant/food place (should be excluded from tourist spots)."""
        name = (item.get("attraction_name") or item.get("name") or item.get("title") or "").lower()
        desc = (item.get("description") or "").lower()
        category = (item.get("category") or "").lower()
        # Explicit restaurant/food fields
        if item.get("restaurant_name"):
            return True
        if "restaurant" in category or "food" in category or "dining" in category or "cafe" in category:
            return True
        # Name or description keywords
        food_keywords = ["restaurant", "cafe", "café", "eatery", "dining", "food court", "grill", "kitchen", "bistro", "bar and grill", "chicken inasal", "manokan"]
        text = f"{name} {desc}"
        return any(kw in text for kw in food_keywords)

    async def _get_tourist_spots(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get tourist spot recommendations from InstantDB: specific places only, no duplicates, no restaurants, match > 50%."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("tourist_spots")
            
            if not scraped_content:
                logger.warning("No scraped content found for tourist_spots in InstantDB")
                return []
            
            # 1) Only specific places: require attraction_name (entity), skip raw page/content records
            # 2) Exclude restaurants/food places
            # 3) Deduplicate by normalized place name
            # 4) Only include match_score > 50%
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            formatted = []
            
            # Placeholder/test entries to exclude from tourist spots
            EXCLUDED_NAMES = {"test attraction", "test", "unknown attraction"}
            
            for item in scraped_content:
                attraction_name = item.get("attraction_name") or item.get("name") or item.get("title")
                # Skip page-level records (no specific place name)
                if not attraction_name or str(attraction_name).strip() in ("", "Unknown Attraction"):
                    continue
                # Skip test/placeholder attractions
                if str(attraction_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                # Skip if it's just a URL or generic title
                raw_url = item.get("url", "")
                if raw_url and attraction_name and (raw_url[:50] in str(attraction_name) or len(str(attraction_name)) < 3):
                    continue
                # Exclude restaurants
                if self._is_restaurant_or_food_place(item):
                    continue
                
                # Deduplicate: normalize name (lower, strip, collapse spaces)
                name_key = " ".join(str(attraction_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": attraction_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link for tourist spots
                    "personality_keywords": item.get("personality_keywords", {}),
                    "opening_hours": item.get("opening_hours"),
                    "entrance_fee": item.get("entrance_fee"),
                    "highlights": item.get("highlights", []),
                    "activities": item.get("activities", []),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                # Format without showing source link (details/website from place only: map + directions)
                formatted_item = self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,  # Don't use sheet URL as "content link"
                    hide_source_link=True,
                )
                formatted.append(formatted_item)
            
            logger.info(f"Tourist spots: {len(formatted)} places (deduped, no restaurants, match > 50%%)")
            return formatted
        except Exception as e:
            logger.error(f"Error getting tourist spots: {e}")
            return []

    async def _get_beaches(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get beach recommendations from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("tourist_spots")
            if not scraped_content:
                return []
            
            # Filter for beaches
            beaches = [item for item in scraped_content if "beach" in (item.get("attraction_name") or item.get("name") or item.get("title", "")).lower()]
            
            # 1) Only specific places: require attraction_name (entity)
            # 2) Deduplicate by normalized place name
            # 3) Only include match_score > 50%
            # 4) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown", "unknown beach", "unknown attraction"}
            formatted = []
            
            for item in beaches:
                attraction_name = item.get("attraction_name") or item.get("name") or item.get("title")
                if not attraction_name or str(attraction_name).strip() in ("", "Unknown Beach", "Unknown Attraction"):
                    continue
                if str(attraction_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                
                # Deduplicate
                name_key = " ".join(str(attraction_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": attraction_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                formatted.append(self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                ))
            return formatted
        except Exception as e:
            logger.error(f"Error getting beaches: {e}")
            return []

    async def _get_mountains(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get mountain/hiking recommendations from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("tourist_spots")
            if not scraped_content:
                return []
            
            # Filter for mountains/hiking
            mountains = [item for item in scraped_content if "mountain" in (item.get("attraction_name") or item.get("name") or item.get("title", "")).lower() or "hiking" in (item.get("description") or "").lower()]
            
            # 1) Only specific places: require attraction_name (entity)
            # 2) Deduplicate by normalized place name
            # 3) Only include match_score > 50%
            # 4) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown", "unknown attraction"}
            formatted = []
            
            for item in mountains:
                attraction_name = item.get("attraction_name") or item.get("name") or item.get("title")
                if not attraction_name or str(attraction_name).strip() in ("", "Unknown Mountain", "Unknown Attraction"):
                    continue
                if str(attraction_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                
                # Deduplicate
                name_key = " ".join(str(attraction_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": attraction_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                formatted.append(self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                ))
            return formatted
        except Exception as e:
            logger.error(f"Error getting mountains: {e}")
            return []

    async def _get_resorts(self, profile, location, curated_details: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Get resort recommendations from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("tourist_spots")
            if not scraped_content:
                return []
            
            # Filter for resorts
            resorts = [item for item in scraped_content if "resort" in (item.get("attraction_name") or item.get("name") or item.get("title", "")).lower()]
            
            # 1) Only specific places: require attraction_name (entity)
            # 2) Deduplicate by normalized place name
            # 3) Only include match_score > 50%
            # 4) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown", "unknown resort", "unknown attraction"}
            formatted = []
            
            for item in resorts:
                attraction_name = item.get("attraction_name") or item.get("name") or item.get("title")
                if not attraction_name or str(attraction_name).strip() in ("", "Unknown Resort", "Unknown Attraction"):
                    continue
                if str(attraction_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                
                # Deduplicate
                name_key = " ".join(str(attraction_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": attraction_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                formatted.append(self._format_recommendation(
                    rec_item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                ))
            return formatted
        except Exception as e:
            logger.error(f"Error getting resorts: {e}")
            return []

    async def _translate_to_english(self, text: str) -> str:
        """Translate text to English using LLM if needed."""
        if not text or not text.strip():
            return text
        
        # Simple check: if text contains mostly English characters and common English words, assume it's already English
        import re
        english_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "about", "into", "through", "during", "including", "against", "among", "throughout", "despite", "towards", "upon", "concerning", "to", "of", "in", "for", "on", "at", "by", "from", "with", "about", "into", "through", "during", "including", "against", "among", "throughout", "despite", "towards", "upon", "concerning"]
        text_lower = text.lower()
        english_word_count = sum(1 for word in english_words if word in text_lower)
        total_words = len(re.findall(r'\b\w+\b', text_lower))
        
        # If more than 30% are English words or text is short, assume English
        if total_words == 0 or (total_words > 0 and english_word_count / total_words > 0.3) or len(text) < 50:
            return text
        
        # Try to translate using LLM
        try:
            from app.config import settings
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a translator. Translate the given text to English. If it's already in English, return it as-is. Only return the translated text, no explanations."},
                        {"role": "user", "content": f"Translate to English: {text[:1000]}"}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                translated = response.choices[0].message.content.strip()
                return translated
        except Exception as e:
            logger.debug(f"Translation failed, using original text: {e}")
        
        return text

    def _normalize_text_for_grouping(self, text: str) -> str:
        """Normalize text for grouping similar topics."""
        if not text:
            return ""
        import re
        # Lowercase, remove extra spaces, remove special chars for comparison
        normalized = re.sub(r'[^\w\s]', '', str(text).lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _are_topics_similar(self, name1: str, name2: str, desc1: str = "", desc2: str = "") -> bool:
        """Check if two topics are similar enough to be merged."""
        norm1 = self._normalize_text_for_grouping(name1)
        norm2 = self._normalize_text_for_grouping(name2)
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Check if one contains the other (e.g., "Pickpocket" vs "Pickpocket Hotspots")
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Check for common keywords
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        common_words = words1.intersection(words2)
        
        # If significant overlap in keywords (at least 2 common words or 50% overlap)
        if len(common_words) >= 2:
            return True
        if len(words1) > 0 and len(words2) > 0:
            overlap_ratio = len(common_words) / max(len(words1), len(words2))
            if overlap_ratio >= 0.5:
                return True
        
        # Check descriptions for similarity
        if desc1 and desc2:
            desc_norm1 = self._normalize_text_for_grouping(desc1[:100])  # First 100 chars
            desc_norm2 = self._normalize_text_for_grouping(desc2[:100])
            desc_words1 = set(desc_norm1.split())
            desc_words2 = set(desc_norm2.split())
            desc_common = desc_words1.intersection(desc_words2)
            if len(desc_common) >= 3:  # At least 3 common words in description
                return True
        
        return False

    def _merge_similar_items(self, items: List[Dict]) -> List[Dict]:
        """Merge correlated/scimilar items into one display."""
        if not items:
            return []
        
        merged = []
        processed_indices = set()
        
        for i, item1 in enumerate(items):
            if i in processed_indices:
                continue
            
            # Start with item1 as base
            merged_item = item1.copy()
            merged_item["merged_count"] = 1
            merged_item["merged_ids"] = [item1.get("id", "")]
            
            # Find similar items
            for j, item2 in enumerate(items[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                name1 = item1.get("name") or item1.get("title", "")
                name2 = item2.get("name") or item2.get("title", "")
                desc1 = item1.get("description", "")
                desc2 = item2.get("description", "")
                
                if self._are_topics_similar(name1, name2, desc1, desc2):
                    # Merge item2 into merged_item
                    # Combine descriptions
                    if desc2 and desc2 not in merged_item.get("description", ""):
                        merged_item["description"] = f"{merged_item.get('description', '')}\n\n{desc2}".strip()
                    
                    # Combine warning signs
                    signs1 = merged_item.get("warning_signs", [])
                    signs2 = item2.get("warning_signs", [])
                    if isinstance(signs1, list) and isinstance(signs2, list):
                        merged_item["warning_signs"] = list(set(signs1 + signs2))
                    elif signs2:
                        merged_item["warning_signs"] = signs2 if isinstance(signs2, list) else [signs2]
                    
                    # Combine how_to_avoid
                    avoid1 = merged_item.get("how_to_avoid", [])
                    avoid2 = item2.get("how_to_avoid", [])
                    if isinstance(avoid1, list) and isinstance(avoid2, list):
                        merged_item["how_to_avoid"] = list(set(avoid1 + avoid2))
                    elif avoid2:
                        merged_item["how_to_avoid"] = avoid2 if isinstance(avoid2, list) else [avoid2]
                    
                    # Use higher severity
                    severity1 = merged_item.get("severity", "medium")
                    severity2 = item2.get("severity", "medium")
                    severity_order = {"high": 3, "medium": 2, "low": 1}
                    if severity_order.get(severity2, 2) > severity_order.get(severity1, 2):
                        merged_item["severity"] = severity2
                    
                    # Combine areas
                    area1 = merged_item.get("area", "")
                    area2 = item2.get("area", "")
                    if area2 and area2 not in area1:
                        merged_item["area"] = f"{area1}, {area2}".strip(", ")
                    
                    merged_item["merged_count"] += 1
                    merged_item["merged_ids"].append(item2.get("id", ""))
                    processed_indices.add(j)
            
            processed_indices.add(i)
            merged.append(merged_item)
        
        logger.info(f"Merged {len(items)} items into {len(merged)} unique topics")
        return merged

    def _is_bacolod_related(self, name: str, description: str = "", area: str = "") -> bool:
        """Check if item is related to Bacolod. Returns False if it's clearly from another location or has malformed data."""
        text = f"{name} {description} {area}".lower()
        
        # Exclude items from other locations
        excluded_keywords = [
            "sulu", "archipelago", "jolo", "basilan", "tawi-tawi",  # Sulu Archipelago
            "manila", "metro manila", "ncr", "quezon city", "makati", "pasay", "taguig",  # Manila area
            "cebu", "davao", "iloilo", "ilo-ilo", "bohol", "palawan",  # Other major cities
            "horse-drawn", "carriage", "kalesa",  # Manila-specific scams
            "marawi", "marawi city",  # Marawi City (not part of Bacolod)
        ]
        
        # Check if text contains excluded keywords
        for keyword in excluded_keywords:
            if keyword in text:
                logger.info(f"Excluding non-Bacolod item: {name[:60]}... (contains '{keyword}')")
                return False
        
        # Exclude items with malformed text (fragmented sentences, incomplete words)
        # Check for patterns like "st, eps", "st, ay", "fog,", "arting," (incomplete words with commas)
        malformed_patterns = [
            r'\b\w{1,2},\s*\w{1,3}\b',  # Short words with comma (e.g., "st, eps", "st, ay")
            r'\b\w{1,3},\s*$',  # Very short word ending with comma at end of text
            r'just do these simple st,',  # Specific malformed pattern
            r'windshield will be fog,',  # Specific malformed pattern
            r'premium st, arting',  # Specific malformed pattern
            r'minimum length of st, ay',  # Specific malformed pattern
        ]
        import re
        for pattern in malformed_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Excluding malformed item: {name[:60]}... (contains malformed text pattern)")
                return False
        
        # Exclude items with suspicious location patterns (multiple repeated locations, fragmented text)
        if area:
            area_lower = area.lower()
            # Check for fragmented location text (contains incomplete sentences)
            if any(fragment in area_lower for fragment in [
                "just do these simple",
                "windshield will be fog",
                "premium st, arting",
                "minimum length of st, ay",
                "recommended minimum length",
                "international travel insurance premium",
            ]):
                logger.info(f"Excluding item with malformed location: {name[:60]}... (location contains fragmented text)")
                return False
            
            # Check for excessive repetition of "Bacolod City, Negros Occidental" (indicates malformed data)
            if area_lower.count("bacolod city, negros occidental") > 2:
                logger.info(f"Excluding item with repeated location: {name[:60]}... (location repeated multiple times)")
                return False
        
        return True
    
    def _clean_references(self, text: str) -> str:
        """Clean text references, replacing non-local references with local alternatives."""
        if not text:
            return text
        
        # Replace Raffy Tulfo references with local police
        text = text.replace("RAFFY TULFO IN ACTION", "local police")
        text = text.replace("Raffy Tulfo in Action", "local police")
        text = text.replace("raffy tulfo in action", "local police")
        text = text.replace("Tulfo", "local police")
        text = text.replace("tulfo", "local police")
        text = text.replace("TV5 Media Center", "local police station")
        text = text.replace("ACTION CENTER", "local police station")
        text = text.replace("action center", "local police station")
        
        return text

    async def _get_scams_and_danger_zones(
        self, location, curated_details: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """Get scams and danger zones from InstantDB scraped content.
        Merges correlated topics and translates to English.
        Filters out items not related to Bacolod."""
        curated_details = curated_details or {}
        official_scams = curated_details.get("scams")
        official_danger = curated_details.get("dangerous_areas")
        
        all_items = []
        
        # Load scams from InstantDB
        scams_content = await self._get_scraped_content_for_category("scams")
        if scams_content:
            logger.info(f"Using {len(scams_content)} scams from InstantDB scraped content")
            for item in scams_content:
                scam_name = item.get("name") or item.get("title", "Unknown Scam")
                description = item.get("description", "")
                area = item.get("location", {}).get("address", "") if isinstance(item.get("location"), dict) else ""
                
                # Filter out non-Bacolod items and malformed data
                if not self._is_bacolod_related(scam_name, description, area):
                    continue
                
                # Clean references (replace Tulfo with local police)
                scam_name = self._clean_references(scam_name)
                description = self._clean_references(description)
                
                # Translate to English
                scam_name = await self._translate_to_english(scam_name)
                description = await self._translate_to_english(description)
                
                # Translate warning signs and how_to_avoid
                warning_signs = item.get("warning_signs", [])
                if isinstance(warning_signs, list):
                    warning_signs = [self._clean_references(await self._translate_to_english(str(sign))) for sign in warning_signs]
                elif warning_signs:
                    warning_signs = [self._clean_references(await self._translate_to_english(str(warning_signs)))]
                
                how_to_avoid = item.get("how_to_avoid", [])
                if isinstance(how_to_avoid, list):
                    how_to_avoid = [self._clean_references(await self._translate_to_english(str(advice))) for advice in how_to_avoid]
                elif how_to_avoid:
                    how_to_avoid = [self._clean_references(await self._translate_to_english(str(how_to_avoid)))]
                
                # Clean area/location
                area_cleaned = item.get("location", {}).get("address", "Bacolod City") if isinstance(item.get("location"), dict) else "Bacolod City"
                area_cleaned = self._clean_references(area_cleaned)
                
                # Filter out malformed areas
                if not self._is_bacolod_related("", "", area_cleaned):
                    continue
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": scam_name,
                    "description": description,
                    "location": item.get("location", {}),
                    "url": item.get("url", official_scams),
                    "type": "scam",
                    "warning_signs": warning_signs,
                    "how_to_avoid": how_to_avoid,
                    "severity": item.get("severity", "medium"),
                    "scam_type": item.get("scam_type"),
                    "area": area_cleaned if area_cleaned and area_cleaned != "Bacolod City" else "Bacolod City, Negros Occidental",
                }
                all_items.append(rec_item)
        
        # Load dangerous areas from InstantDB
        danger_content = await self._get_scraped_content_for_category("dangerous_areas")
        if danger_content:
            logger.info(f"Using {len(danger_content)} dangerous areas from InstantDB scraped content")
            for item in danger_content:
                danger_name = item.get("name") or item.get("title", "Unknown Danger")
                description = item.get("description", "")
                area = item.get("location", {}).get("address", "") if isinstance(item.get("location"), dict) else ""
                
                # Filter out non-Bacolod items and malformed data
                if not self._is_bacolod_related(danger_name, description, area):
                    continue
                
                # Clean references (replace Tulfo with local police)
                danger_name = self._clean_references(danger_name)
                description = self._clean_references(description)
                
                # Translate to English
                danger_name = await self._translate_to_english(danger_name)
                description = await self._translate_to_english(description)
                
                # Translate warning signs and how_to_avoid
                warning_signs = item.get("warning_signs", [])
                if isinstance(warning_signs, list):
                    warning_signs = [self._clean_references(await self._translate_to_english(str(sign))) for sign in warning_signs]
                elif warning_signs:
                    warning_signs = [self._clean_references(await self._translate_to_english(str(warning_signs)))]
                
                how_to_avoid = item.get("how_to_avoid", [])
                if isinstance(how_to_avoid, list):
                    how_to_avoid = [self._clean_references(await self._translate_to_english(str(advice))) for advice in how_to_avoid]
                elif how_to_avoid:
                    how_to_avoid = [self._clean_references(await self._translate_to_english(str(how_to_avoid)))]
                
                # Clean area/location
                area_cleaned = item.get("location", {}).get("address", "Bacolod City") if isinstance(item.get("location"), dict) else "Bacolod City"
                area_cleaned = self._clean_references(area_cleaned)
                
                # Filter out malformed areas
                if not self._is_bacolod_related("", "", area_cleaned):
                    continue
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": danger_name,
                    "description": description,
                    "location": item.get("location", {}),
                    "url": item.get("url", official_danger),
                    "type": "danger_zone",
                    "warning_signs": warning_signs,
                    "how_to_avoid": how_to_avoid,
                    "severity": item.get("severity", "medium"),
                    "type_of_danger": item.get("type_of_danger"),
                    "area": area_cleaned if area_cleaned and area_cleaned != "Bacolod City" else "Bacolod City, Negros Occidental",
                }
                all_items.append(rec_item)
        
        # Merge correlated topics
        merged_items = self._merge_similar_items(all_items)
        
        # Format merged items
        formatted = []
        for item in merged_items:
            advice_text = ", ".join(item.get("how_to_avoid", [])) if item.get("how_to_avoid") else ("Stay alert and verify information" if item.get("type") == "scam" else "Stay alert and avoid the area")
            
            formatted_item = self._format_recommendation(item, 0.0, details_fallback_url=official_scams if item.get("type") == "scam" else official_danger)
            formatted_item["type"] = item.get("type")
            formatted_item["area"] = item.get("area", "Bacolod City")
            formatted_item["advice"] = advice_text
            formatted_item["warning_signs"] = item.get("warning_signs", [])
            formatted_item["how_to_avoid"] = item.get("how_to_avoid", [])
            formatted_item["severity"] = item.get("severity", "medium")
            if item.get("type") == "scam" and official_scams:
                formatted_item["links"]["official"] = official_scams
            elif item.get("type") == "danger_zone" and official_danger:
                formatted_item["links"]["official"] = official_danger
            formatted.append(formatted_item)
        
        # Fallback to hardcoded if no InstantDB data (for backward compatibility)
        if not formatted:
            logger.warning("No scraped content found for scams/dangerous_areas, using fallback")
            scams_and_dangers = [
            {
                "id": "scam_001",
                "name": "Fake Tour Packages",
                "description": "Beware of unauthorized tour operators offering suspiciously cheap packages. Always book through licensed travel agencies or verified online platforms.",
                "type": "scam",
                "area": "Tourist areas, malls, and transportation hubs",
                "advice": "Verify tour operator credentials, check reviews, and avoid paying upfront for suspiciously low prices.",
                "warning_signs": ["Suspiciously low prices", "No credentials shown", "Pressure to pay immediately"],
                "how_to_avoid": ["Verify tour operator credentials", "Check reviews", "Avoid paying upfront for suspiciously low prices"],
                "severity": "high",
                "official_link": official_scams or "https://www.tourism.gov.ph",
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
                "warning_signs": ["Crowded areas", "Festival events", "Public markets"],
                "how_to_avoid": ["Use anti-theft bags", "Keep wallets in front pockets", "Avoid carrying large amounts of cash", "Stay alert in crowded places"],
                "severity": "medium",
                "official_link": official_danger or "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6742,
                    "longitude": 122.9513,
                    "address": "Downtown Bacolod, Public Market Area"
                }
            },
            {
                "id": "scam_002",
                "name": "Overpriced Taxi/Jeepney Rides",
                "description": "Some drivers may charge tourists higher rates. Always ask for the meter or agree on a price before starting the trip.",
                "type": "scam",
                "area": "Airport, Bus Terminals, Tourist Spots",
                "advice": "Use ride-hailing apps (Grab) when possible, or negotiate prices upfront. Know approximate distances and typical fares.",
                "warning_signs": ["No meter", "Refusal to use meter", "Unusually high quoted price"],
                "how_to_avoid": ["Use ride-hailing apps (Grab)", "Negotiate prices upfront", "Know approximate distances and typical fares"],
                "severity": "medium",
                "official_link": official_scams or "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6426,
                    "longitude": 122.9297,
                    "address": "Bacolod-Silay Airport, Silay City"
                }
            },
            {
                "id": "danger_002",
                "name": "Unsafe Areas at Night",
                "description": "Some areas in Bacolod are less safe after dark. Avoid walking alone in poorly lit areas, especially away from main tourist zones.",
                "type": "danger_zone",
                "area": "Outskirts, Industrial Areas, Some Barangays",
                "advice": "Use transportation at night, stay in well-lit areas, travel in groups when possible, and inform your accommodation of your plans.",
                "warning_signs": ["Poorly lit areas", "Isolated locations", "Away from main tourist zones"],
                "how_to_avoid": ["Use transportation at night", "Stay in well-lit areas", "Travel in groups when possible", "Inform your accommodation of your plans"],
                "severity": "medium",
                "official_link": official_danger or "https://www.bacolodcity.gov.ph",
                "location": {
                    "latitude": 10.6815,
                    "longitude": 122.9420,
                    "address": "Bacolod City Outskirts, Industrial Area"
                }
            }
        ]
        
            # Format fallback items (already in English, no translation needed)
            formatted_fallback = []
            for item in scams_and_dangers:
                formatted_item = self._format_recommendation(item, 0.0)
                formatted_item["type"] = item.get("type")
                formatted_item["area"] = item.get("area")
                formatted_item["advice"] = item.get("advice")
                formatted_item["warning_signs"] = item.get("warning_signs", [])
                formatted_item["how_to_avoid"] = item.get("how_to_avoid", [])
                formatted_item["severity"] = item.get("severity", "medium")
                if item.get("official_link"):
                    formatted_item["links"]["official"] = item["official_link"]
                formatted_fallback.append(formatted_item)
            formatted.extend(formatted_fallback)
        
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

    async def _get_secret_spots(
        self,
        profile,
        location,
        already_recommended_names: Optional[set] = None,
        curated_details: Optional[Dict[str, str]] = None,
    ) -> List[Dict]:
        """Get secret spots from InstantDB: specific places only, no duplicates, match > 50%, no content link."""
        curated_details = curated_details or {}
        try:
            scraped_content = await self._get_scraped_content_for_category("secret_places")
            
            if not scraped_content:
                logger.warning("No scraped content found for secret_places in InstantDB")
                return []
            
            if already_recommended_names is None:
                already_recommended_names = set()
            
            # 1) Only specific places: require place_name (entity), skip raw page/content records
            # 2) Deduplicate by normalized place name
            # 3) Only include match_score > 50%
            # 4) Hide source/content link
            seen_names: set = set()
            MIN_MATCH = 0.5  # 50%
            EXCLUDED_NAMES = {"test", "unknown place", "unknown", "unknown attraction"}
            secret_candidates = []
            
            for item in scraped_content:
                place_name = item.get("place_name") or item.get("name") or item.get("title")
                # Skip page-level records (no specific place name)
                if not place_name or str(place_name).strip() in ("", "Unknown Place", "Unknown"):
                    continue
                # Skip test/placeholder places
                if str(place_name).strip().lower() in EXCLUDED_NAMES:
                    continue
                # Skip if it's just a URL or generic title
                raw_url = item.get("url", "")
                if raw_url and place_name and (raw_url[:50] in str(place_name) or len(str(place_name)) < 3):
                    continue
                # Skip if already recommended in other categories
                if str(place_name).lower().strip() in already_recommended_names:
                    continue
                
                # Deduplicate: normalize name (lower, strip, collapse spaces)
                name_key = " ".join(str(place_name).lower().strip().split())
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                rec_item = {
                    "id": item.get("id", ""),
                    "name": place_name,
                    "description": item.get("description", ""),
                    "address": item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None),
                    "location": item.get("location", {}),
                    "images": item.get("images", []),
                    "url": "",  # Do NOT expose source/content link
                    "personality_keywords": item.get("personality_keywords", {}),
                    "why_secret": item.get("why_secret"),
                    "how_to_find": item.get("how_to_find"),
                    "tips": item.get("tips", []),
                }
                
                match_score = self._calculate_match_score(rec_item, profile.personality)
                if match_score <= MIN_MATCH:
                    continue
                
                secret_candidates.append((rec_item, match_score))
            
            # Sort by match score and take top 2
            secret_candidates.sort(key=lambda x: x[1], reverse=True)
            secret_items = [item for item, score in secret_candidates[:2]]
            
            formatted = []
            for item, match_score in secret_candidates[:2]:  # Already filtered, deduped, and sorted
                formatted_item = self._format_recommendation(
                    item, match_score,
                    details_fallback_url=None,
                    hide_source_link=True,
                )
                
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
