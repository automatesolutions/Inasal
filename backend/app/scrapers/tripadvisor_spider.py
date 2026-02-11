"""
Scrapy spider for TripAdvisor URLs.
Targets: tripadvisor.com.ph (hotels, attractions, reviews)
"""

import scrapy
import json
import logging
import re
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

from app.extractors.location_extractor import LocationExtractor
from app.extractors.event_extractor import EventExtractor

logger = logging.getLogger(__name__)


class TripAdvisorSpider(scrapy.Spider):
    """Scrapy spider for TripAdvisor pages"""
    
    name = 'tripadvisor'
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 8,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, url: str, category: str = "accommodation_hotels", *args, **kwargs):
        super(TripAdvisorSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]
        self.category = category
        self.scraped_data = {}
        self.location_extractor = LocationExtractor()
        self.event_extractor = EventExtractor()
    
    def parse(self, response):
        """Parse TripAdvisor page"""
        try:
            html = response.text
            
            # Extract title
            title = None
            title_selectors = [
                'h1[data-automation="mainH1"]::text',
                'h1::text',
                'meta[property="og:title"]::attr(content)',
                '.heading_title::text',
            ]
            for selector in title_selectors:
                title = response.css(selector).get()
                if title:
                    title = title.strip()
                    break
            
            # Extract description
            description = None
            desc_selectors = [
                'meta[property="og:description"]::attr(content)',
                'meta[name="description"]::attr(content)',
                '.description::text',
                '[data-automation="description"]::text',
            ]
            for selector in desc_selectors:
                desc = response.css(selector).get()
                if desc and len(desc.strip()) > 50:
                    description = desc.strip()
                    break
            
            # Extract rating
            rating = None
            rating_selectors = [
                '[data-automation="rating"]::attr(aria-label)',
                '.rating::text',
                '[class*="rating"]::text',
            ]
            for selector in rating_selectors:
                rating_text = response.css(selector).get()
                if rating_text:
                    # Extract number from rating text (e.g., "4.5 out of 5")
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        try:
                            rating = float(rating_match.group(1))
                        except ValueError:
                            pass
                    break
            
            # Extract address/location
            address = None
            address_selectors = [
                '[data-automation="address"]::text',
                '.address::text',
                '[class*="address"]::text',
            ]
            for selector in address_selectors:
                addr = response.css(selector).get()
                if addr:
                    address = addr.strip()
                    break
            
            # Extract main content (reviews summary, details)
            content_text = ""
            content_selectors = [
                '[data-automation="description"]',
                '.description',
                '.review',
                'article',
            ]
            for selector in content_selectors:
                content_elem = response.css(selector)
                if content_elem:
                    content_text = " ".join(content_elem.css('::text').getall()).strip()
                    if len(content_text) > 200:
                        break
            
            # Limit content length
            if len(content_text) > 10000:
                content_text = content_text[:10000] + "..."
            
            # Extract images
            images = []
            img_selectors = [
                '[data-automation="photo"] img::attr(src)',
                '.photo img::attr(src)',
                'meta[property="og:image"]::attr(content)',
                'img[class*="photo"]::attr(src)',
            ]
            for selector in img_selectors:
                imgs = response.css(selector).getall()
                for img in imgs[:10]:
                    if img and img.startswith("http"):
                        images.append(img)
                    elif img and img.startswith("/"):
                        parsed = urlparse(response.url)
                        images.append(f"{parsed.scheme}://{parsed.netloc}{img}")
                if images:
                    break
            
            # Extract amenities (for hotels)
            amenities = []
            amenity_selectors = [
                '[data-automation="amenity"]::text',
                '.amenity::text',
                '[class*="amenity"]::text',
            ]
            for selector in amenity_selectors:
                amens = response.css(selector).getall()
                amenities.extend([a.strip() for a in amens if a.strip()])
            
            # Extract places mentioned
            places_mentioned = self._extract_places(content_text, title or "", description or "", address or "")
            
            # Extract location (with coordinates if available)
            location = self.location_extractor.extract_location(html, response.url, content_text)
            if not location and address:
                # If no location extracted, create one from address
                location = {
                    "address": address,
                    "city": "Bacolod City",
                    "region": "Negros Occidental",
                }
            
            # Extract events (usually none for TripAdvisor, but check)
            events = self.event_extractor.extract_events(html, content_text)
            
            # Extract personality keywords
            personality_keywords = self._extract_personality_keywords(content_text, description or "", title or "")
            
            self.scraped_data = {
                "url": response.url,
                "category": self.category,
                "title": title or "Untitled",
                "description": description or content_text[:500] if content_text else "",
                "content_text": content_text,
                "images": images[:5],
                "places_mentioned": places_mentioned,
                "location": location,
                "events": events,
                "personality_keywords": personality_keywords,
                "rating": rating,
                "amenities": amenities[:10] if amenities else [],
                "domain": urlparse(response.url).netloc,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped TripAdvisor: {response.url}")
            return self.scraped_data
            
        except Exception as e:
            logger.error(f"Error parsing TripAdvisor {response.url}: {e}")
            return {
                "url": response.url,
                "category": self.category,
                "title": None,
                "description": None,
                "content_text": "",
                "images": [],
                "places_mentioned": [],
                "location": None,
                "events": [],
                "personality_keywords": {},
                "rating": None,
                "amenities": [],
                "domain": urlparse(response.url).netloc,
                "scraped_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def _extract_places(self, *texts: str) -> list:
        """Extract Bacolod-related place names"""
        combined = " ".join(t for t in texts if t)
        places = []
        
        patterns = [
            r"\b(Bacolod\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:in|at|near)\s+Bacolod\b",
            r"\b(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Museum|Park|Beach|Resort|Hotel|Restaurant|Cafe|Church|Cathedral|Plaza|Market)\b",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            for match in matches:
                place = match.strip() if isinstance(match, str) else " ".join(match).strip()
                if place and place not in places and len(place) < 100:
                    places.append(place)
        
        return places[:20]
    
    def _extract_personality_keywords(self, *texts: str) -> Dict[str, float]:
        """Extract personality-relevant keywords"""
        combined = " ".join(t for t in texts if t).lower()
        
        trait_keywords = {
            "adventurous": ["adventure", "hiking", "outdoor", "extreme", "thrilling"],
            "cultural": ["culture", "heritage", "museum", "historical", "tradition", "festival"],
            "foodie": ["food", "restaurant", "cuisine", "delicacy", "dining", "cafe", "bakery"],
            "nature_lover": ["nature", "beach", "park", "garden", "scenic", "view", "sunset"],
            "history_buff": ["history", "historical", "heritage", "ancient", "ruins", "monument"],
            "social": ["festival", "celebration", "event", "nightlife", "bar", "club", "entertainment"],
        }
        
        personality_scores = {}
        for trait, keywords in trait_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in combined)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            personality_scores[trait] = round(score, 2)
        
        return personality_scores
