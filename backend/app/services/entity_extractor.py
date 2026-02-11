"""
Entity extraction service using LLM to extract multiple entities from scraped content.
For example, extract multiple hotels from a "Top 10 Hotels" article, or multiple restaurants from a food guide.
"""

import logging
from typing import Dict, Any, List, Optional
import json
import re

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract multiple entities (hotels, restaurants, etc.) from scraped content using LLM"""
    
    def __init__(self):
        self.llm_client = None
        self.llm_provider = None
        try:
            from app.config import settings
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                try:
                    from openai import AsyncOpenAI
                    self.llm_client = AsyncOpenAI(api_key=settings.openai_api_key)
                    self.llm_provider = "openai"
                except ImportError:
                    logger.warning("OpenAI library not installed")
            elif hasattr(settings, 'ollama_base_url') and settings.ollama_base_url:
                self.ollama_base_url = settings.ollama_base_url
                self.llm_provider = "ollama"
            else:
                logger.warning("No LLM provider configured for entity extraction")
        except Exception as e:
            logger.warning(f"Could not initialize LLM client: {e}")
    
    async def extract_entities(self, content: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
        """
        Extract multiple entities from scraped content based on category.
        
        Returns a list of entities, each as a separate record to be saved.
        For example:
        - accommodation_hotels: List of hotels with name, address, description, images, etc.
        - restaurants_food: List of restaurants with name, address, cuisine, description, etc.
        - tourist_spots: List of attractions with name, address, description, etc.
        """
        if not self.llm_client and self.llm_provider != "ollama":
            logger.debug("LLM not available, returning single entity")
            return [content]  # Return original content as single entity
        
        try:
            # Build prompt for entity extraction
            prompt = self._build_entity_extraction_prompt(content, category)
            
            # Call LLM
            entities_json = await self._call_llm(prompt, category)
            
            if entities_json and isinstance(entities_json, list) and len(entities_json) > 0:
                # Process each entity
                extracted_entities = []
                for entity_data in entities_json:
                    # Merge with original content metadata
                    entity = {
                        **content,  # Keep original fields
                        **entity_data,  # Override with extracted entity data
                    }
                    extracted_entities.append(entity)
                
                logger.info(f"✅ Extracted {len(extracted_entities)} entities from {category} content")
                return extracted_entities
            else:
                logger.warning(f"⚠️  LLM returned no entities, using original content")
                return [content]
                
        except Exception as e:
            logger.error(f"❌ Error extracting entities: {e}")
            return [content]
    
    def _build_entity_extraction_prompt(self, content: Dict[str, Any], category: str) -> str:
        """Build LLM prompt for extracting multiple entities"""
        
        title = content.get("title", "")
        description = content.get("description", "")
        # For Facebook/blog pages, use more content
        max_content = 15000 if "facebook.com" in content.get("url", "").lower() else 8000
        content_text = content.get("content_text", "")[:max_content]
        url = content.get("url", "")
        
        if category == "accommodation_hotels":
            return f"""Extract ALL hotels and accommodations mentioned in the following content. 
IMPORTANT: Extract EVERY single hotel/accommodation mentioned, even if only the name is given. Each hotel should be a separate item.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:4000]}

Extract EVERY hotel, resort, inn, hostel, bed & breakfast, or accommodation mentioned. Look for:
- Hotel names (e.g., "L'Fisher Hotel", "Seda Hotel", "Go Hotels")
- Resorts and inns
- Hostels and budget accommodations
- Any place where travelers can stay

Return a JSON array where each item represents one accommodation with these fields:

[
  {{
    "hotel_name": "exact name of the hotel/accommodation",
    "address": "full address including street, city, province",
    "phone": "contact phone number if mentioned",
    "email": "contact email if mentioned",
    "website": "official website URL if different from source",
    "description": "detailed description of this specific hotel",
    "images": ["url1", "url2", ...],  // Images specific to this hotel
    "amenities": ["WiFi", "Pool", "Restaurant", ...],  // List of amenities
    "room_types": ["Standard", "Deluxe", ...],  // Room types if mentioned
    "price_range": "price range or starting price",
    "rating": "rating out of 5 or 10 if mentioned",
    "check_in_time": "check-in time",
    "check_out_time": "check-out time",
    "policies": "cancellation policy or other policies"
  }},
  ...
]

Return ONLY a valid JSON array. If no hotels are found, return an empty array []. Do not include markdown formatting."""

        elif category == "restaurants_food":
            return f"""You are extracting restaurant entities from travel blog content, food blog posts, or social media pages about food. Extract ALL restaurants, cafes, food establishments, food stalls, eateries, and dining places mentioned.

CRITICAL INSTRUCTIONS:
- Extract EVERY single restaurant/food place mentioned, even if only the name is given
- If the content is from a food blog or Facebook page, look for restaurants mentioned in posts, reviews, or recommendations
- If the article says "Top 10 Restaurants" or lists multiple restaurants, extract ALL of them
- Each restaurant should be a separate item in the JSON array
- Look for restaurant names, food places, cafes, eateries mentioned anywhere in the content
- For Facebook pages or food blogs: Extract restaurants that the blogger visited, reviewed, or recommended
- Extract restaurant names even if they appear in post descriptions, comments, or captions
- IMPORTANT: Even if the content is limited (like a Facebook page description), look for ANY restaurant names, food places, or dining establishments mentioned
- If you see phrases like "visited [restaurant name]", "tried [restaurant]", "recommend [place]", extract those restaurant names
- Look for proper nouns that might be restaurant names (e.g., "Manokan Country", "Calea", "Bob's", etc.)

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:12000]}

Extract EVERY restaurant, cafe, food stall, eatery, or dining establishment mentioned. Look for:
- Restaurant names (e.g., "Manokan Country", "Calea", "Bob's Restaurant")
- Food places mentioned in lists or articles
- Cafes and coffee shops
- Food stalls and markets
- Any place where food is served

Return a JSON array where each item represents one restaurant:

[
  {{
    "restaurant_name": "exact name of the restaurant (REQUIRED - extract even if only name is mentioned)",
    "address": "full address including street, city, province (if mentioned)",
    "phone": "contact phone number if mentioned",
    "email": "contact email if mentioned",
    "website": "official website URL if different from source",
    "description": "detailed description of this specific restaurant, what makes it special, what they serve",
    "images": ["url1", "url2", ...],  // Images specific to this restaurant from the content
    "cuisine_type": "type of cuisine (e.g., Filipino, Italian, Fast Food, Bakery, Seafood)",
    "specialties": ["signature dish 1", "signature dish 2", ...],  // Signature dishes or what they're known for
    "price_range": "price range (e.g., budget-friendly, mid-range, fine dining)",
    "opening_hours": "opening hours or schedule if mentioned",
    "rating": "rating out of 5 or 10 if mentioned",
    "features": ["outdoor seating", "parking", "wifi", ...],  // Features
    "reservations": "whether reservations are required or available"
  }},
  ...
]

CRITICAL: If the article mentions "Top 10 Restaurants" or lists multiple restaurants, extract ALL of them as separate items.
If only restaurant names are mentioned without details, still extract them with at least the restaurant_name field.

Return ONLY a valid JSON array. If no restaurants are found, return an empty array []. Do not include markdown formatting."""

        elif category == "tourist_spots":
            return f"""Extract ALL tourist spots, attractions, landmarks, hidden gems, and places of interest mentioned in the following content. Each attraction should be a separate item.

CRITICAL INSTRUCTIONS:
- Extract EVERY single tourist spot/attraction mentioned, even if only the name is given
- Look for places in lists like "Top 10", "Must-Visit", "Best Places", etc.
- For travel blogs: Extract all places mentioned in itineraries or recommendations
- For Reddit/social media: Extract places mentioned in posts and comments
- For booking sites: Extract each listed attraction or activity
- Each tourist spot should be a separate item in the JSON array

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:12000]}

Extract EVERY tourist spot, attraction, landmark, hidden gem, or place of interest mentioned. Look for:
- Historical sites and landmarks
- Museums and cultural centers
- Parks and natural attractions
- Viewpoints and scenic spots
- Religious sites (churches, temples)
- Activities and experiences
- Places mentioned in travel guides or itineraries

Return a JSON array:

[
  {{
    "attraction_name": "exact name of the tourist spot/attraction (REQUIRED - extract even if only name is mentioned)",
    "address": "full address including street, city, province (if mentioned)",
    "description": "detailed description of this specific attraction, what makes it special, what visitors can see/do",
    "images": ["url1", "url2", ...],  // Images specific to this attraction from the content
    "opening_hours": "opening hours or schedule (if mentioned)",
    "entrance_fee": "entrance fee or admission cost (if mentioned)",
    "best_time_to_visit": "best time of day or season to visit (if mentioned)",
    "duration": "recommended duration of visit (if mentioned)",
    "highlights": ["highlight 1", "highlight 2", ...],  // Main highlights or key features
    "activities": ["activity 1", "activity 2", ...],  // Available activities or things to do
    "contact_info": "phone number or contact information (if mentioned)",
    "parking": "parking availability (if mentioned)",
    "accessibility": "accessibility information (if mentioned)",
    "category": "type of attraction (e.g., historical site, museum, park, viewpoint, church)"
  }},
  ...
]

CRITICAL: If the content mentions multiple tourist spots (e.g., "Top 10 Attractions", "Best Places to Visit"), extract ALL of them as separate items.
If only attraction names are mentioned without details, still extract them with at least the attraction_name field.

Return ONLY a valid JSON array. If no attractions are found, return an empty array []. Do not include markdown formatting."""

        elif category == "secret_places":
            return f"""Extract ALL secret places, hidden gems, off-the-beaten-path locations, hidden cafes, secret gardens, and unique spots mentioned in the following content. Each place should be a separate item.

CRITICAL INSTRUCTIONS:
- Extract EVERY single secret place/hidden gem mentioned, even if only the name is given
- Look for places described as "secret", "hidden", "off-the-beaten-path", "lesser-known", "local favorite"
- For Facebook posts/videos: Extract places mentioned in posts, comments, or descriptions
- For directory listings: Extract each individual place listed
- Each secret place should be a separate item in the JSON array

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:12000]}

Extract EVERY secret place, hidden gem, hidden cafe, secret garden, or unique location mentioned. Look for:
- Secret cafes and restaurants
- Hidden gardens or parks
- Off-the-beaten-path spots
- Local favorites not widely known
- Places mentioned in social media posts
- Locations in directory listings

Return a JSON array:

[
  {{
    "place_name": "exact name of the secret place (REQUIRED - extract even if only name is mentioned)",
    "address": "full address or location description (if mentioned)",
    "description": "detailed description of this specific place, what makes it special, what visitors can do there",
    "images": ["url1", "url2", ...],  // Images specific to this place from the content
    "why_secret": "why this is considered a secret or hidden gem, what makes it special",
    "best_time_to_visit": "best time of day or season to visit (if mentioned)",
    "how_to_find": "directions or how to find this place, landmarks nearby",
    "what_to_expect": "what visitors can expect when they visit",
    "tips": ["tip 1", "tip 2", ...],  // Tips for visitors, what to bring, what to know
    "category": "type of place (e.g., cafe, garden, viewpoint, restaurant, bar)"
  }},
  ...
]

CRITICAL: If the content mentions multiple secret places (e.g., "Top 10 Hidden Gems"), extract ALL of them as separate items.
If only place names are mentioned without details, still extract them with at least the place_name field.

Return ONLY a valid JSON array. If no places are found, return an empty array []. Do not include markdown formatting."""

        elif category == "dangerous_areas":
            return f"""Extract ALL dangerous areas, safety warnings, travel advisories, and security concerns mentioned in the following content. Each warning or area should be a separate entry.

CRITICAL INSTRUCTIONS:
- Extract EVERY dangerous area, safety concern, or warning mentioned, even if only briefly mentioned
- Look for specific neighborhoods, streets, areas, or types of locations mentioned as unsafe
- Extract travel advisories and safety recommendations
- For government sites: Extract all specific warnings and areas mentioned
- For news articles: Extract reported incidents and affected areas
- Each dangerous area or warning should be a separate item in the JSON array

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:12000]}

Extract EVERY dangerous area, safety warning, or security concern mentioned. Look for:
- Specific neighborhoods or districts mentioned as unsafe
- Types of crimes or dangers (theft, scams, violence, etc.)
- Times or situations when areas are more dangerous
- Travel advisories and warnings
- Reported incidents and affected locations

Return a JSON array:

[
  {{
    "name": "name or title of the dangerous area/warning (REQUIRED - extract even if only briefly mentioned)",
    "location": "specific location, neighborhood, street, or area where this danger occurs (if mentioned)",
    "description": "detailed description of the danger, what makes this area unsafe, what types of incidents occur",
    "warning_signs": ["sign 1", "sign 2", ...],  // Warning signs to watch for, red flags
    "how_to_avoid": ["tip 1", "tip 2", ...],  // How to avoid or stay safe, safety tips
    "severity": "severity level (low, medium, high, critical) based on content",
    "reported_incidents": "any reported incidents, statistics, or examples if mentioned",
    "time_of_concern": "specific times when area is more dangerous (e.g., night, late hours) if mentioned",
    "type_of_danger": "type of danger (e.g., theft, violence, scams, natural hazards)"
  }},
  ...
]

CRITICAL: If the content mentions multiple dangerous areas or warnings, extract ALL of them as separate items.
If only area names or brief warnings are mentioned, still extract them with at least the name and description fields.

Return ONLY a valid JSON array. If no items are found, return an empty array []. Do not include markdown formatting."""

        elif category == "scams":
            return f"""Extract ALL scams, fraud schemes, and deceptive practices mentioned in the following content. Each scam should be a separate entry.

CRITICAL INSTRUCTIONS:
- Extract EVERY scam or fraud scheme mentioned, even if only briefly described
- Look for specific scam types (car scams, love scams, investment scams, etc.)
- For news articles: Extract all scams mentioned in the article
- For Reddit/social media: Extract scams mentioned in posts and comments
- For commercial sites: Extract scam warnings and types mentioned
- Each scam should be a separate item in the JSON array

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:12000]}

Extract EVERY scam, fraud scheme, or deceptive practice mentioned. Look for:
- Car scams (used car fraud, vehicle scams)
- Love scams and romance fraud
- Investment scams and Ponzi schemes
- Online scams and phishing
- Street scams and tourist scams
- Real estate scams
- Any other fraudulent schemes

Return a JSON array:

[
  {{
    "name": "name or title of the scam (REQUIRED - extract even if only briefly mentioned)",
    "location": "location or area where this scam occurs (if mentioned)",
    "description": "detailed description of how the scam works, what victims are told, how it operates",
    "warning_signs": ["sign 1", "sign 2", ...],  // Warning signs, red flags, how to identify the scam
    "how_to_avoid": ["tip 1", "tip 2", ...],  // How to avoid falling victim, protective measures
    "severity": "severity level (low, medium, high) based on impact",
    "reported_incidents": "any reported incidents, victim counts, or examples if mentioned",
    "scam_type": "type of scam (e.g., car scam, love scam, investment scam, online scam)",
    "target_victims": "who is typically targeted (e.g., tourists, car buyers, investors) if mentioned",
    "common_tactics": ["tactic 1", "tactic 2", ...]  // Common tactics used by scammers
  }},
  ...
]

CRITICAL: If the content mentions multiple scams (e.g., "Top 10 Scams", "Common Scams"), extract ALL of them as separate items.
If only scam names or brief descriptions are mentioned, still extract them with at least the name and description fields.

Return ONLY a valid JSON array. If no items are found, return an empty array []. Do not include markdown formatting."""

        else:
            # Generic extraction
            return f"""Extract ALL relevant items mentioned in the following content. Each item should be a separate entry.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:3000]}

Extract EVERY relevant item mentioned. Return a JSON array:

[
  {{
    "name": "name or title of the item",
    "address": "address or location if mentioned",
    "description": "detailed description",
    "images": ["url1", "url2", ...],
    "key_details": ["detail 1", "detail 2", ...]
  }},
  ...
]

Return ONLY a valid JSON array. If no items are found, return an empty array []. Do not include markdown formatting."""
    
    async def _call_llm(self, prompt: str, category: str) -> Optional[List[Dict[str, Any]]]:
        """Call LLM to extract entities"""
        try:
            if self.llm_provider == "openai" and self.llm_client:
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that extracts structured information from text. Always return valid JSON arrays only. Extract ALL entities mentioned, not just one. If an article lists 10 restaurants, extract all 10 as separate items."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=6000  # More tokens for multiple entities
                )
                content = response.choices[0].message.content.strip()
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # Parse JSON
                entities = json.loads(content)
                if isinstance(entities, list):
                    return entities
                elif isinstance(entities, dict):
                    return [entities]  # Single entity wrapped in dict
                else:
                    return []
            
            elif self.llm_provider == "ollama":
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.ollama_base_url}/api/generate",
                        json={
                            "model": "llama3.2",
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1
                            }
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("response", "").strip()
                        # Try to extract JSON array from response
                        json_match = re.search(r'\[.*\]', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        # Try parsing entire response
                        try:
                            parsed = json.loads(content)
                            if isinstance(parsed, list):
                                return parsed
                            elif isinstance(parsed, dict):
                                return [parsed]
                        except:
                            pass
                        return []
            
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content[:500] if 'content' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return []


# Global instance
entity_extractor = EntityExtractor()
