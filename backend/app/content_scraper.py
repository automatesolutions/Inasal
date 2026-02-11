"""
Content scraper for URLs from Google Sheet.
Extracts structured information (title, description, places, locations, events, personality keywords) from web pages.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.extractors.location_extractor import LocationExtractor
from app.extractors.event_extractor import EventExtractor

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SCRAPE_TIMEOUT = 30.0


class ContentScraper:
    """Scrape and extract structured content from web pages"""

    def __init__(self):
        self.bright_data_client = None
        self.location_extractor = LocationExtractor()
        self.event_extractor = EventExtractor()
        try:
            from app.bright_data_client import bright_data_client
            # Check if Bright Data is available (has API key)
            if bright_data_client._api_key or bright_data_client._web_unlocker_api_key:
                self.bright_data_client = bright_data_client
        except Exception:
            pass

    async def scrape_url(self, url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a URL and extract structured content.
        Uses Bright Data Web Unlocker for all URLs to maximize success rate.
        Returns dict with: title, description, content_text, places_mentioned, images, etc.
        """
        try:
            # Always try Bright Data Web Unlocker first (handles JS-heavy sites, Facebook, Reddit, etc.)
            if self.bright_data_client:
                logger.debug(f"Using Bright Data Web Unlocker for {url[:60]}...")
                # For Facebook, we need more content - but Web Unlocker API doesn't support wait_for parameter
                # It automatically waits and renders JavaScript
                html = await self.bright_data_client.scrape_with_web_unlocker(
                    url, wait_for=None, render=True
                )
                if html:
                    content = self._extract_content(html, url, category)
                    # Note: Entity extraction happens in sheets_sync.py after scraping
                    return content
                else:
                    logger.warning(f"Bright Data Web Unlocker returned no HTML for {url[:60]}...")
            
            # Fallback: direct HTTP request (only if Bright Data fails)
            logger.debug(f"Falling back to direct HTTP for {url[:60]}...")
            async with httpx.AsyncClient(
                timeout=SCRAPE_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
                content = self._extract_content(html, url, category)
                # Enrich with LLM even for fallback
                if content:
                    try:
                        from app.services.llm_enrichment import llm_enrichment_service
                        content = await llm_enrichment_service.enrich_content(content, category)
                    except Exception as e:
                        logger.warning(f"LLM enrichment failed: {e}")
                return content
        except Exception as e:
            logger.warning(f"Failed to scrape {url[:80]}...: {e}")
            return None

    def _extract_content(self, html: str, url: str, category: str) -> Dict[str, Any]:
        """Extract structured content from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Extract title
        title = None
        for selector in ['meta[property="og:title"]', 'title', 'h1']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.get("content") or tag.get_text(strip=True)
                if title:
                    break
        
        # Extract description
        description = None
        for selector in [
            'meta[property="og:description"]',
            'meta[name="description"]',
            'article p',
            'div[class*="description"] p',
        ]:
            tag = soup.select_one(selector)
            if tag:
                description = tag.get("content") or tag.get_text(strip=True)
                if description and len(description) > 50:
                    break
        
        # Extract main content text first (needed for URL pattern matching)
        content_text = ""
        
        # For Facebook pages, extract all meaningful text content more aggressively
        if "facebook.com" in url.lower():
            # Get ALL text from body, then filter intelligently
            body_text = soup.find("body")
            if body_text:
                # Get all text with better structure - preserve line breaks for context
                all_text = body_text.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in all_text.split("\n") if line.strip()]
                
                # Filter meaningful content - look for posts, descriptions, restaurant mentions
                filtered_lines = []
                skip_keywords = ["log in", "sign up", "cookie", "privacy", "terms", "create account", 
                               "forgot password", "email or phone", "password", "see all", "see more",
                               "what are meta", "manage your ad", "other ways", "accounts centre"]
                
                # Keywords that suggest restaurant/food content
                food_keywords = ["restaurant", "cafe", "food", "eat", "dining", "dish", "menu", "cuisine",
                               "chicken", "cansi", "inasal", "piaya", "bacolod", "visited", "tried", "recommend"]
                
                for line in lines:
                    line_lower = line.lower()
                    # Include lines that:
                    # 1. Are meaningful length (not too short, not too long)
                    # 2. Don't match skip keywords
                    # 3. Are not pure numbers
                    # 4. Are unique
                    # 5. OR contain food-related keywords (even if shorter)
                    is_food_related = any(keyword in line_lower for keyword in food_keywords)
                    is_good_length = 15 <= len(line) <= 1500
                    should_skip = any(skip in line_lower for skip in skip_keywords)
                    is_number = line.replace(",", "").replace(".", "").isdigit()
                    
                    if ((is_good_length or is_food_related) and 
                        not should_skip and 
                        not is_number and 
                        line not in filtered_lines):
                        filtered_lines.append(line)
                        if len(filtered_lines) >= 200:  # Get much more content for Facebook
                            break
                
                if filtered_lines:
                    content_text = "\n".join(filtered_lines)
        
        # Try article tag first (for regular websites)
        if not content_text:
            article = soup.find("article")
            if article:
                content_text = article.get_text(separator=" ", strip=True)
        
        # Try main content areas
        if not content_text or len(content_text) < 500:
            for selector in ['main', 'div[class*="content"]', 'div[class*="post"]', 'body']:
                tag = soup.select_one(selector)
                if tag:
                    text = tag.get_text(separator=" ", strip=True)
                    if len(text) > len(content_text):
                        content_text = text
        
        # Limit content length (but allow more for Facebook pages)
        max_length = 20000 if "facebook.com" in url.lower() else 10000
        if len(content_text) > max_length:
            content_text = content_text[:max_length] + "..."
        
        # Extract website links mentioned on the page (especially for Facebook pages)
        # Do this AFTER content_text is extracted so we can search in text
        website_links = []
        if "facebook.com" in url.lower():
            # Look for links in the page - check both href and text content
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                # Normalize href (handle relative URLs)
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                
                # Look for website links (not Facebook/internal social media links)
                if (href and 
                    ("http" in href) and 
                    ("facebook.com" not in href.lower()) and
                    ("instagram.com" not in href.lower()) and
                    ("twitter.com" not in href.lower()) and
                    ("linkedin.com" not in href.lower()) and
                    ("youtube.com" not in href.lower()) and
                    len(href) < 200 and
                    href not in website_links):
                    website_links.append(href)
                    if len(website_links) >= 5:  # Limit to first 5 links
                        break
            
            # Also check text content for website URLs (Facebook sometimes embeds URLs in text)
            if content_text:
                import re
                url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?'
                for text_url_match in re.finditer(url_pattern, content_text):
                    found_url = text_url_match.group(0)
                    if ("facebook.com" not in found_url.lower() and
                        "instagram.com" not in found_url.lower() and
                        "twitter.com" not in found_url.lower() and
                        found_url not in website_links):
                        website_links.append(found_url)
                        if len(website_links) >= 5:
                            break
        
        # Extract images
        images = []
        for img in soup.find_all("img", limit=10):
            src = img.get("src") or img.get("data-src")
            if src:
                # Make absolute URL
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                elif not src.startswith("http"):
                    continue
                images.append(src)
        
        # Extract places mentioned (Bacolod-related keywords)
        places_mentioned = self._extract_places(content_text, title or "", description or "")
        
        # Extract location information
        location = self.location_extractor.extract_location(html, url, content_text)
        
        # Extract events
        events = self.event_extractor.extract_events(html, content_text)
        
        # Extract personality keywords from content
        personality_keywords = self._extract_personality_keywords(content_text, description or "", title or "")
        
        result = {
            "url": url,
            "category": category,
            "title": title or "Untitled",
            "description": description or content_text[:500] if content_text else "",
            "content_text": content_text,
            "images": images[:5],  # Limit to 5 images
            "places_mentioned": places_mentioned,
            "location": location,  # NEW: {address, latitude, longitude, city, region}
            "events": events,  # NEW: [{name, start_date, end_date, location, description}]
            "personality_keywords": personality_keywords,  # NEW: {adventurous, cultural, foodie, ...}
            "domain": urlparse(url).netloc,
        }
        
        # Add website links if found (for Facebook pages)
        if website_links:
            result["website_links"] = website_links
        
        return result

    def _extract_places(self, *texts: str) -> List[str]:
        """Extract Bacolod-related place names from text"""
        combined = " ".join(t for t in texts if t)
        places = []
        
        # Common Bacolod place patterns
        patterns = [
            r"\b(Bacolod\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",  # "Bacolod City", "Bacolod Public Market"
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:in|at|near)\s+Bacolod\b",  # "MassKara Festival in Bacolod"
            r"\b(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Museum|Park|Beach|Resort|Hotel|Restaurant|Cafe|Church|Cathedral|Plaza|Market)\b",  # "The Ruins", "San Sebastian Cathedral"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            for match in matches:
                place = match.strip() if isinstance(match, str) else " ".join(match).strip()
                if place and place not in places and len(place) < 100:
                    places.append(place)
        
        # Also look for common Bacolod attractions
        common_places = [
            "The Ruins", "San Sebastian Cathedral", "MassKara Festival",
            "Negros Museum", "Bacolod Public Market", "Lacson Street",
            "Campuestohan Highland Resort", "Mambukal Resort", "Punta Taytay",
        ]
        for place in common_places:
            if place.lower() in combined.lower() and place not in places:
                places.append(place)
        
        return places[:20]  # Limit to 20 places

    def _extract_personality_keywords(self, *texts: str) -> Dict[str, float]:
        """Extract personality-relevant keywords from content and score them (0-1)"""
        combined = " ".join(t for t in texts if t).lower()
        
        # Keyword patterns for each personality trait
        trait_keywords = {
            "adventurous": [
                "adventure", "hiking", "trekking", "outdoor", "extreme", "thrilling",
                "zip line", "climbing", "exploring", "exciting", "action", "sports",
                "waterfall", "mountain", "trail", "camping", "backpacking"
            ],
            "cultural": [
                "culture", "heritage", "museum", "historical", "tradition", "festival",
                "art", "gallery", "monument", "cathedral", "church", "architecture",
                "local", "indigenous", "folklore", "dance", "music", "performance"
            ],
            "foodie": [
                "food", "restaurant", "cuisine", "delicacy", "dish", "meal", "dining",
                "cafe", "bakery", "market", "street food", "local food", "specialty",
                "chicken inasal", "cansi", "piaya", "napoleones", "taste", "flavor"
            ],
            "nature_lover": [
                "nature", "beach", "park", "garden", "forest", "wildlife", "bird",
                "scenic", "view", "sunset", "sunrise", "landscape", "eco", "resort",
                "waterfall", "mountain", "lake", "river", "tropical", "flora", "fauna"
            ],
            "history_buff": [
                "history", "historical", "heritage", "ancient", "ruins", "monument",
                "museum", "colonial", "past", "era", "century", "archaeological",
                "preservation", "landmark", "memorial", "site", "artifacts"
            ],
            "social": [
                "festival", "celebration", "event", "party", "gathering", "meetup",
                "nightlife", "bar", "club", "entertainment", "social", "community",
                "people", "crowd", "vibrant", "lively", "fun", "enjoyment"
            ]
        }
        
        personality_scores = {}
        for trait, keywords in trait_keywords.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword in combined)
            # Score: 0.0 to 1.0 based on number of matches (normalized)
            score = min(1.0, matches / max(len(keywords) * 0.3, 1))  # Scale to 0-1
            personality_scores[trait] = round(score, 2)
        
        return personality_scores
