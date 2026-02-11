"""
Async wrapper to run Scrapy spiders programmatically.
Routes URLs to appropriate spider based on domain and integrates with Bright Data middleware.
"""

import logging
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from app.scrapers.travel_blog_spider import TravelBlogSpider
from app.scrapers.tripadvisor_spider import TripAdvisorSpider
from app.scrapers.facebook_content_spider import FacebookContentSpider
from app.scrapers.news_spider import NewsSpider
from app.scrapers.generic_web_spider import GenericWebSpider

logger = logging.getLogger(__name__)


class ScrapyRunner:
    """Run Scrapy spiders programmatically with Bright Data proxy support"""
    
    def __init__(self):
        self.scraped_data_cache = {}
    
    def _get_spider_for_url(self, url: str) -> type:
        """Determine which spider to use based on URL domain"""
        domain = urlparse(url).netloc.lower()
        
        # Travel blogs
        travel_blog_domains = [
            "philippineshiddengems.com",
            "lakbaypinas.com",
            "thepinaysolobackpacker.com",
            "wanderlust.com.ph",
            "traveloka.com",
        ]
        if any(td in domain for td in travel_blog_domains):
            return TravelBlogSpider
        
        # TripAdvisor
        if "tripadvisor" in domain:
            return TripAdvisorSpider
        
        # Facebook
        if "facebook.com" in domain or "fb.com" in domain:
            return FacebookContentSpider
        
        # News sites
        news_domains = [
            "gmanetwork.com",
            "abs-cbn.com",
            "mb.com.ph",
            "philstar.com",
            "rappler.com",
            "inquirer.net",
        ]
        if any(nd in domain for nd in news_domains):
            return NewsSpider
        
        # Default: generic spider
        return GenericWebSpider
    
    async def run_spider(self, url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Run appropriate Scrapy spider for a URL and return scraped data.
        Returns None if scraping fails.
        """
        spider_class = self._get_spider_for_url(url)
        spider_name = spider_class.name
        
        logger.info(f"Running {spider_name} spider for {url}")
        
        # Run spider in executor to avoid blocking
        loop = asyncio.get_event_loop()
        scraped_data = await loop.run_in_executor(
            None,
            self._run_spider_sync,
            spider_class,
            url,
            category
        )
        
        return scraped_data
    
    def _run_spider_sync(self, spider_class: type, url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Run Scrapy spider synchronously and return scraped data.
        This runs in a thread executor to avoid blocking the event loop.
        """
        scraped_data = {}
        data_captured = False
        
        # Suppress stderr to prevent signal errors
        import sys
        from contextlib import redirect_stderr
        from io import StringIO
        stderr_buffer = StringIO()
        
        # Configure Scrapy settings
        scrapy_settings = get_project_settings()
        
        # Disable signal handlers and problematic extensions
        scrapy_settings.set('LOG_ENABLED', True)
        scrapy_settings.set('LOG_LEVEL', 'ERROR')
        
        scrapy_settings.set('EXTENSIONS', {
            'scrapy.extensions.corestats.CoreStats': None,
        })
        
        # Import custom settings
        try:
            import app.scrapers.scrapy_settings as custom_settings
            for key in dir(custom_settings):
                if not key.startswith('_') and key.isupper():
                    try:
                        scrapy_settings.set(key, getattr(custom_settings, key))
                    except Exception:
                        pass
        except ImportError:
            logger.warning("Could not import custom Scrapy settings, using defaults")
        
        # Configure Bright Data proxy middleware
        try:
            from app.scrapers.proxy_middleware import BrightDataProxyMiddleware
            from app.config import settings
            
            username = settings.bright_data_residential_username
            password = settings.bright_data_residential_password
            endpoint = settings.bright_data_residential_endpoint or "brd.superproxy.io:33335"
            
            if username and password:
                scrapy_settings.set('HTTPPROXY_ENABLED', True)
                scrapy_settings.set('HTTPPROXY_AUTH_ENCODING', 'latin-1')
                logger.info(f"Using Bright Data Residential Proxy")
                
                scrapy_settings.set('DOWNLOADER_MIDDLEWARES', {
                    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
                    'app.scrapers.proxy_middleware.BrightDataProxyMiddleware': 100,
                })
        except Exception as e:
            logger.warning(f"Could not configure Bright Data proxy: {e}")
        
        scrapy_settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        scrapy_settings.set('ROBOTSTXT_OBEY', False)
        
        # Create spider instance to capture data
        spider_instance = spider_class(url=url, category=category)
        
        # Create crawler process
        process = CrawlerProcess(scrapy_settings)
        
        # Run spider
        try:
            with redirect_stderr(stderr_buffer):
                process.crawl(spider_class, url=url, category=category)
                process.start()
        except Exception as e:
            logger.error(f"Error running {spider_class.name} spider: {e}")
            return None
        
        # Get scraped data from spider instance
        if hasattr(spider_instance, 'scraped_data') and spider_instance.scraped_data:
            return spider_instance.scraped_data
        
        return None
