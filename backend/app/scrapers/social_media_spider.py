"""Scrapy spiders for Facebook/Instagram profile scraping"""

import scrapy
from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FacebookProfileSpider(scrapy.Spider):
    """Scrapy spider to scrape Facebook profile data"""
    
    name = 'facebook_profile'
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, profile_url: str, *args, **kwargs):
        super(FacebookProfileSpider, self).__init__(*args, **kwargs)
        self.profile_url = profile_url
        self.start_urls = [profile_url]
        self.scraped_data = {}
    
    def parse(self, response):
        """Parse Facebook profile page"""
        try:
            # Extract bio from meta tags (most reliable)
            bio = response.css('meta[property="og:description"]::attr(content)').get()
            if not bio:
                # Try alternative selectors
                bio = response.css('div[data-testid="profile-bio"]::text').get()
                if not bio:
                    bio = response.css('div[class*="bio"]::text').get()
            
            # Extract location
            location = response.css('span[data-testid="profile-location"]::text').get()
            if not location:
                location = response.css('a[href*="/places/"]::text').get()
            
            # Extract profile picture
            profile_pic = response.css('meta[property="og:image"]::attr(content)').get()
            if not profile_pic:
                profile_pic = response.css('img[data-testid="profile-picture"]::attr(src)').get()
            
            # Extract posts (first few visible posts)
            posts = []
            post_selectors = [
                'div[data-pagelet="FeedUnit"]',
                'div[role="article"]',
                'div[class*="userContent"]'
            ]
            
            for selector in post_selectors:
                post_texts = response.css(f'{selector}::text').getall()
                if post_texts:
                    posts = [p.strip() for p in post_texts[:10] if p.strip()]
                    break
            
            # Extract interests/tags (pages they like)
            interests = []
            interest_selectors = [
                'a[href*="/pages/"]::text',
                'a[href*="/groups/"]::text',
                'div[class*="interest"]::text'
            ]
            
            for selector in interest_selectors:
                interest_texts = response.css(selector).getall()
                if interest_texts:
                    interests = [i.strip() for i in interest_texts[:10] if i.strip()]
                    break
            
            self.scraped_data = {
                "bio": bio.strip() if bio else None,
                "posts_content": posts,
                "interests": interests,
                "location": location.strip() if location else None,
                "profile_picture": profile_pic,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped Facebook profile: {self.profile_url}")
            return self.scraped_data
            
        except Exception as e:
            logger.error(f"Error parsing Facebook profile {self.profile_url}: {e}")
            return {
                "bio": None,
                "posts_content": [],
                "interests": [],
                "location": None,
                "profile_picture": None,
                "scraped_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }


class InstagramProfileSpider(scrapy.Spider):
    """Scrapy spider to scrape Instagram profile data"""
    
    name = 'instagram_profile'
    custom_settings = {
        'DOWNLOAD_DELAY': 4,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 3,
        'AUTOTHROTTLE_MAX_DELAY': 15,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, profile_url: str, *args, **kwargs):
        super(InstagramProfileSpider, self).__init__(*args, **kwargs)
        self.profile_url = profile_url
        self.start_urls = [profile_url]
        self.scraped_data = {}
    
    def parse(self, response):
        """Parse Instagram profile page"""
        try:
            # Extract bio from meta tags
            bio = response.css('meta[property="og:description"]::attr(content)').get()
            if not bio:
                bio = response.css('meta[name="description"]::attr(content)').get()
            
            # Extract profile picture
            profile_pic = response.css('meta[property="og:image"]::attr(content)').get()
            if not profile_pic:
                profile_pic = response.css('img[alt*="profile picture"]::attr(src)').get()
            
            # Extract location (if in bio or profile)
            location = None
            location_selectors = [
                'a[href*="/explore/locations/"]::text',
                'span[class*="location"]::text'
            ]
            for selector in location_selectors:
                loc = response.css(selector).get()
                if loc:
                    location = loc.strip()
                    break
            
            # Extract posts (captions from recent posts)
            posts = []
            # Instagram uses JSON-LD for structured data
            json_scripts = response.css('script[type="application/ld+json"]::text').getall()
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script)
                    if isinstance(data, dict) and 'caption' in data:
                        posts.append(data['caption'])
                except:
                    pass
            
            # Also try extracting from HTML
            if not posts:
                post_captions = response.css('article img::attr(alt)').getall()
                posts = [p for p in post_captions[:10] if p and p.strip()]
            
            # Extract interests/hashtags
            interests = []
            hashtags = response.css('a[href*="/explore/tags/"]::text').getall()
            interests = [h.strip() for h in hashtags[:10] if h.strip()]
            
            self.scraped_data = {
                "bio": bio.strip() if bio else None,
                "posts_content": posts,
                "interests": interests,
                "location": location,
                "profile_picture": profile_pic,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped Instagram profile: {self.profile_url}")
            return self.scraped_data
            
        except Exception as e:
            logger.error(f"Error parsing Instagram profile {self.profile_url}: {e}")
            return {
                "bio": None,
                "posts_content": [],
                "interests": [],
                "location": None,
                "profile_picture": None,
                "scraped_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
