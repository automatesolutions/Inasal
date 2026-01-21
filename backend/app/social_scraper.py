"""Social media profile scraping using Bright Data Residential Proxy + Scrapy"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from app.bright_data_client import bright_data_client
from app.config import settings
from app.scrapers.social_media_spider import FacebookProfileSpider, InstagramProfileSpider

logger = logging.getLogger(__name__)


class SocialMediaScraper:
    """Scrape social media profiles using Bright Data Residential Proxy + Scrapy"""

    def __init__(self):
        self.bright_data = bright_data_client
        self.scraped_data_cache = {}  # Cache to store scraped data
    
    def _get_bright_data_proxy(self) -> Optional[str]:
        """Get Bright Data Residential Proxy URL"""
        # Bright Data Residential Proxy format:
        # http://{USERNAME}:{PASSWORD}@{ENDPOINT}
        
        username = settings.bright_data_residential_username
        password = settings.bright_data_residential_password
        endpoint = settings.bright_data_residential_endpoint or "brd.superproxy.io:33335"
        
        if not username or not password:
            logger.warning("Bright Data Residential Proxy not configured. Scraping will fail.")
            return None
        
        proxy_url = f"http://{username}:{password}@{endpoint}"
        return proxy_url
    
    def _run_scrapy_spider(self, spider_class, profile_url: str) -> Dict[str, Any]:
        """Run Scrapy spider synchronously and return scraped data"""
        scraped_data = {}
        data_captured = False
        
        # Determine platform name for error handling
        platform_name = "facebook" if "facebook" in spider_class.name.lower() else "instagram"
        
        # Configure Scrapy settings
        scrapy_settings = get_project_settings()
        
        # Import our custom settings
        try:
            import app.scrapers.scrapy_settings as custom_settings
            # Update settings from custom_settings module
            for key in dir(custom_settings):
                if not key.startswith('_') and key.isupper():
                    try:
                        scrapy_settings.set(key, getattr(custom_settings, key))
                    except Exception:
                        pass  # Skip settings that can't be set
        except ImportError:
            logger.warning("Could not import custom Scrapy settings, using defaults")
        
        # Configure Bright Data Residential Proxy
        proxy_url = self._get_bright_data_proxy()
        if proxy_url:
            scrapy_settings.set('HTTPPROXY_ENABLED', True)
            scrapy_settings.set('HTTPPROXY_AUTH_ENCODING', 'latin-1')
            logger.info(f"Using Bright Data Residential Proxy: {proxy_url[:50]}...")
        else:
            logger.warning("Bright Data proxy not configured, scraping may fail")
        
        # User agent
        scrapy_settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        scrapy_settings.set('ROBOTSTXT_OBEY', False)
        
        # Use our custom proxy middleware
        scrapy_settings.set('DOWNLOADER_MIDDLEWARES', {
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
            'app.scrapers.proxy_middleware.BrightDataProxyMiddleware': 100,
        })
        
        # Create a custom spider that captures data
        class DataCaptureSpider(spider_class):
            def parse(self, response):
                result = super().parse(response)
                nonlocal scraped_data, data_captured
                if isinstance(result, dict):
                    scraped_data = result
                    data_captured = True
                return result
        
        # Create crawler process
        # Note: CrawlerProcess can only be instantiated once per process
        # We use install_root_handler=False to avoid Twisted reactor conflicts
        process = CrawlerProcess(scrapy_settings, install_root_handler=False)
        
        # Run spider
        try:
            process.crawl(DataCaptureSpider, profile_url=profile_url)
            # Start the process (this blocks until spider completes)
            process.start()
        except Exception as e:
            logger.error(f"Error running Scrapy spider: {e}", exc_info=True)
            return self._get_empty_scraped_data(platform=platform_name, profile_url=profile_url)
        
        if not data_captured:
            logger.warning(f"No data captured from {profile_url}")
            return self._get_empty_scraped_data(platform=platform_name, profile_url=profile_url)
        
        return scraped_data
    
    def _get_empty_scraped_data(self, platform: str, profile_url: str) -> Dict[str, Any]:
        """Return empty scraped data structure"""
        from datetime import datetime
        return {
            "bio": None,
            "posts_content": [],
            "interests": [],
            "location": None,
            "profile_picture": None,
            "scraped_at": datetime.utcnow().isoformat(),
            "error": "Scraping failed or returned no data"
        }

    async def search_social_profiles(
        self,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for Facebook and Instagram profiles using Bright Data
        """
        full_name = f"{first_name} {last_name}"
        
        results = {
            "facebook_profiles": [],
            "instagram_profiles": [],
            "search_query": full_name,
            "phone_number": phone_number
        }
        
        try:
            # Search Facebook profiles via Google search
            facebook_query = f'"{first_name} {last_name}" site:facebook.com'
            facebook_results = await self.bright_data.search_public(
                source="google",
                query=facebook_query,
                limit=5
            )
            
            if facebook_results.get("success") and facebook_results.get("results"):
                results["facebook_profiles"] = facebook_results["results"]
            
            # Search Instagram profiles via Google search
            instagram_query = f'"{first_name} {last_name}" site:instagram.com'
            instagram_results = await self.bright_data.search_public(
                source="google",
                query=instagram_query,
                limit=5
            )
            
            if instagram_results.get("success") and instagram_results.get("results"):
                results["instagram_profiles"] = instagram_results["results"]
                
        except Exception as e:
            logger.error(f"Error searching social profiles: {e}")
            # Return empty results on error
        
        return results

    async def scrape_profile_data(
        self,
        profile_url: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Scrape actual profile data from Facebook/Instagram URL
        Using Scrapy with Bright Data Residential Proxy
        """
        try:
            # Select appropriate spider
            if platform.lower() == "facebook":
                spider_class = FacebookProfileSpider
            elif platform.lower() == "instagram":
                spider_class = InstagramProfileSpider
            else:
                logger.warning(f"Unknown platform: {platform}, using Facebook spider")
                spider_class = FacebookProfileSpider
            
            # Run Scrapy spider in thread pool (Scrapy is synchronous, but we're async)
            loop = asyncio.get_event_loop()
            
            # Run spider in executor (Scrapy blocks, so run in thread)
            scraped_data = await loop.run_in_executor(
                None,
                self._run_scrapy_spider,
                spider_class,
                profile_url
            )
            
            # Add provider and URL to result
            result = {
                "provider": platform,
                "profile_url": profile_url,
                "bio": scraped_data.get("bio"),
                "posts_content": scraped_data.get("posts_content", []),
                "interests": scraped_data.get("interests", []),
                "location": scraped_data.get("location"),
                "profile_picture": scraped_data.get("profile_picture"),
                "scraped_at": scraped_data.get("scraped_at"),
            }
            
            # Add error if present
            if "error" in scraped_data:
                result["error"] = scraped_data["error"]
            
            logger.info(f"Successfully scraped {platform} profile: {profile_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {platform} profile {profile_url}: {e}", exc_info=True)
            from datetime import datetime
            return {
                "provider": platform,
                "profile_url": profile_url,
                "bio": None,
                "posts_content": [],
                "interests": [],
                "location": None,
                "profile_picture": None,
                "scraped_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
