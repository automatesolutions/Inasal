"""
Scrapy spider for Facebook posts/pages.
Targets: Facebook URLs (posts, pages, videos)
Note: Facebook requires JavaScript rendering, so Bright Data Web Unlocker should be used.
"""

import scrapy
import json
import logging
import re
from typing import Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from app.extractors.location_extractor import LocationExtractor
from app.extractors.event_extractor import EventExtractor

logger = logging.getLogger(__name__)


class FacebookContentSpider(scrapy.Spider):
    """Scrapy spider for Facebook content (posts, pages, videos)"""
    
    name = 'facebook_content'
    custom_settings = {
        'DOWNLOAD_DELAY': 4,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 3,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, url: str, category: str = "secret_places", *args, **kwargs):
        super(FacebookContentSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]
        self.category = category
        self.scraped_data = {}
        self.location_extractor = LocationExtractor()
        self.event_extractor = EventExtractor()
    
    def parse(self, response):
        """Parse Facebook page/post"""
        try:
            html = response.text
            
            # Extract title (from meta tags - most reliable for Facebook)
            title = None
            title_selectors = [
                'meta[property="og:title"]::attr(content)',
                'meta[name="title"]::attr(content)',
                'title::text',
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
            ]
            for selector in desc_selectors:
                desc = response.css(selector).get()
                if desc and len(desc.strip()) > 50:
                    description = desc.strip()
                    break
            
            # Extract post content (from meta tags or structured data)
            content_text = description or ""
            
            # Try to extract from JSON-LD or structured data
            json_scripts = response.css('script[type="application/ld+json"]::text').getall()
            for script in json_scripts:
                try:
                    data = json.loads(script)
                    if isinstance(data, dict):
                        if data.get("description") and len(data["description"]) > len(content_text):
                            content_text = data["description"]
                        if data.get("articleBody"):
                            content_text = data["articleBody"]
                except json.JSONDecodeError:
                    pass
            
            # Extract images
            images = []
            img_selectors = [
                'meta[property="og:image"]::attr(content)',
                'meta[name="og:image"]::attr(content)',
                'img[data-src]::attr(data-src)',
                'img::attr(src)',
            ]
            for selector in img_selectors:
                imgs = response.css(selector).getall()
                for img in imgs[:10]:
                    if img and img.startswith("http"):
                        images.append(img)
                if images:
                    break
            
            # Extract location from Facebook location tags
            location_text = None
            location_selectors = [
                'a[href*="/places/"]::text',
                '[data-testid="location"]::text',
                '.location::text',
            ]
            for selector in location_selectors:
                loc = response.css(selector).get()
                if loc:
                    location_text = loc.strip()
                    break
            
            # Extract places mentioned
            places_mentioned = self._extract_places(content_text, title or "", description or "", location_text or "")
            
            # Extract location
            location = self.location_extractor.extract_location(html, response.url, content_text)
            if not location and location_text:
                location = {
                    "address": location_text,
                    "city": "Bacolod City",
                    "region": "Negros Occidental",
                }
            
            # Extract events (Facebook often has event info)
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
                "domain": urlparse(response.url).netloc,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped Facebook content: {response.url}")
            return self.scraped_data
            
        except Exception as e:
            logger.error(f"Error parsing Facebook {response.url}: {e}")
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
        
        # Common Bacolod places from Facebook posts
        common_places = [
            "Commis Co", "EL Gon's Secret Garden", "Hidden Cafe",
            "The Ruins", "San Sebastian Cathedral", "MassKara Festival",
        ]
        for place in common_places:
            if place.lower() in combined.lower() and place not in places:
                places.append(place)
        
        return places[:20]
    
    def _extract_personality_keywords(self, *texts: str) -> Dict[str, float]:
        """Extract personality-relevant keywords"""
        combined = " ".join(t for t in texts if t).lower()
        
        trait_keywords = {
            "adventurous": ["adventure", "hiking", "outdoor", "exploring", "exciting"],
            "cultural": ["culture", "heritage", "museum", "historical", "tradition", "festival"],
            "foodie": ["food", "restaurant", "cuisine", "delicacy", "dining", "cafe", "bakery", "hidden"],
            "nature_lover": ["nature", "beach", "park", "garden", "scenic", "view"],
            "history_buff": ["history", "historical", "heritage", "ancient", "ruins"],
            "social": ["festival", "celebration", "event", "gathering", "meetup", "secret", "hidden"],
        }
        
        personality_scores = {}
        for trait, keywords in trait_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in combined)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))
            personality_scores[trait] = round(score, 2)
        
        return personality_scores
