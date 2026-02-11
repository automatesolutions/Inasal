"""
LLM-based enrichment service to extract structured data from scraped content.
Extracts hotel names, addresses, restaurant details, etc. using LLM.
"""

import logging
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)


class LLMEnrichmentService:
    """Enrich scraped content with structured data extracted using LLM"""
    
    def __init__(self):
        self.llm_client = None
        try:
            # Try to import Ollama or OpenAI client
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
                logger.warning("No LLM provider configured for enrichment")
        except Exception as e:
            logger.warning(f"Could not initialize LLM client: {e}")
    
    async def enrich_content(self, content: Dict[str, Any], category: str) -> Dict[str, Any]:
        """
        Enrich scraped content with structured data based on category.
        
        For hotels: Extract name, address, amenities, ratings, contact info
        For restaurants: Extract name, address, cuisine type, hours, ratings, contact info
        For tourist spots: Extract name, address, opening hours, entrance fees, best time to visit
        """
        if not self.llm_client and self.llm_provider != "ollama":
            logger.debug("LLM not available, skipping enrichment")
            return content
        
        try:
            # Build prompt based on category
            prompt = self._build_enrichment_prompt(content, category)
            
            # Call LLM
            enriched_data = await self._call_llm(prompt, category)
            
            # Merge enriched data into content
            if enriched_data:
                content.update(enriched_data)
                logger.info(f"✅ Enriched content with structured data for {category}")
            else:
                logger.warning(f"⚠️  LLM enrichment returned no data for {category}")
            
            return content
        except Exception as e:
            logger.error(f"❌ Error enriching content: {e}")
            return content
    
    def _build_enrichment_prompt(self, content: Dict[str, Any], category: str) -> str:
        """Build LLM prompt for extracting structured data"""
        
        title = content.get("title", "")
        description = content.get("description", "")
        content_text = content.get("content_text", "")[:2000]  # Limit text length
        url = content.get("url", "")
        
        if category == "accommodation_hotels":
            return f"""Extract structured information about hotels/accommodations from the following content.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:1500]}

Extract the following information in JSON format:
{{
    "hotel_name": "exact name of the hotel/accommodation",
    "address": "full address including street, city, province",
    "phone": "contact phone number if mentioned",
    "email": "contact email if mentioned",
    "website": "official website URL if different from source",
    "amenities": ["list", "of", "amenities", "mentioned"],
    "room_types": ["list", "of", "room", "types", "if", "mentioned"],
    "price_range": "price range or starting price if mentioned",
    "rating": "rating out of 5 or 10 if mentioned",
    "check_in_time": "check-in time if mentioned",
    "check_out_time": "check-out time if mentioned",
    "policies": "cancellation policy or other policies if mentioned"
}}

Return ONLY valid JSON, no markdown formatting, no explanations. If information is not available, use null or empty string/array."""

        elif category == "restaurants_food":
            return f"""Extract structured information about restaurants/food establishments from the following content.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:1500]}

Extract the following information in JSON format:
{{
    "restaurant_name": "exact name of the restaurant/food establishment",
    "address": "full address including street, city, province",
    "phone": "contact phone number if mentioned",
    "email": "contact email if mentioned",
    "website": "official website URL if different from source",
    "cuisine_type": "type of cuisine (e.g., Filipino, Italian, Fast Food)",
    "specialties": ["list", "of", "signature", "dishes", "or", "specialties"],
    "price_range": "price range (e.g., budget-friendly, mid-range, fine dining)",
    "opening_hours": "opening hours or schedule if mentioned",
    "rating": "rating out of 5 or 10 if mentioned",
    "features": ["list", "of", "features", "like", "outdoor", "seating", "parking", "wifi", "etc"],
    "reservations": "whether reservations are required or available"
}}

Return ONLY valid JSON, no markdown formatting, no explanations. If information is not available, use null or empty string/array."""

        elif category == "tourist_spots":
            return f"""Extract structured information about tourist spots/attractions from the following content.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:1500]}

Extract the following information in JSON format:
{{
    "attraction_name": "exact name of the tourist spot/attraction",
    "address": "full address including street, city, province",
    "opening_hours": "opening hours or schedule if mentioned",
    "entrance_fee": "entrance fee or admission cost if mentioned",
    "best_time_to_visit": "best time of day or season to visit if mentioned",
    "duration": "recommended duration of visit if mentioned",
    "highlights": ["list", "of", "main", "highlights", "or", "features"],
    "activities": ["list", "of", "activities", "available", "at", "the", "location"],
    "contact_info": "phone number or contact information if mentioned",
    "parking": "parking availability if mentioned",
    "accessibility": "accessibility information if mentioned"
}}

Return ONLY valid JSON, no markdown formatting, no explanations. If information is not available, use null or empty string/array."""

        else:
            # Generic enrichment for other categories
            return f"""Extract structured information from the following content.

URL: {url}
Title: {title}
Description: {description}
Content: {content_text[:1500]}

Extract key information in JSON format:
{{
    "name": "main name or title of the entity",
    "address": "full address if mentioned",
    "contact_info": "phone, email, or other contact information if mentioned",
    "key_details": ["list", "of", "important", "details", "or", "features"],
    "pricing": "pricing information if mentioned",
    "schedule": "schedule, hours, or timing if mentioned"
}}

Return ONLY valid JSON, no markdown formatting, no explanations. If information is not available, use null or empty string/array."""
    
    async def _call_llm(self, prompt: str, category: str) -> Optional[Dict[str, Any]]:
        """Call LLM to extract structured data"""
        try:
            if self.llm_provider == "openai" and self.llm_client:
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",  # Use cost-effective model
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that extracts structured information from text. Always return valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temperature for consistent extraction
                    max_tokens=1000
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
                
                return json.loads(content)
            
            elif self.llm_provider == "ollama":
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.ollama_base_url}/api/generate",
                        json={
                            "model": "llama3.2",  # or whatever model is available
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
                        # Try to extract JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        return json.loads(content)
            
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content[:500] if 'content' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None


# Global instance
llm_enrichment_service = LLMEnrichmentService()
