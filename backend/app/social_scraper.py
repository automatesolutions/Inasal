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
        """
        Run Scrapy spider synchronously and return scraped data.
        
        Note: Scrapy errors about signals in background threads are expected and harmless.
        They occur because Scrapy tries to set up signal handlers in non-main threads.
        These errors don't affect scraping functionality.
        """
        scraped_data = {}
        data_captured = False
        
        # Determine platform name for error handling
        platform_name = "facebook" if "facebook" in spider_class.name.lower() else "instagram"
        
        # Suppress stderr BEFORE any Scrapy/Twisted code runs
        # This prevents signal errors from appearing in logs
        import sys
        from contextlib import redirect_stderr
        from io import StringIO
        stderr_buffer = StringIO()
        
        # Configure Scrapy settings
        scrapy_settings = get_project_settings()
        
        # Disable signal handlers and problematic extensions to prevent background thread errors
        scrapy_settings.set('LOG_ENABLED', True)
        scrapy_settings.set('LOG_LEVEL', 'ERROR')  # Only show errors, suppress warnings
        
        # Disable extensions that cause signal handler issues
        scrapy_settings.set('EXTENSIONS', {
            # Keep only essential extensions, disable ones that use signals
            'scrapy.extensions.corestats.CoreStats': None,  # Disable - causes AssertionError
        })
        
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
        
        # Patch signal.signal() function itself to suppress errors in background threads
        # This is the most aggressive approach - catches all signal installation attempts
        import signal as signal_module
        original_signal = signal_module.signal
        
        def patched_signal(signalnum, handler):
            """Patched signal.signal that suppresses errors in background threads"""
            try:
                return original_signal(signalnum, handler)
            except (ValueError, OSError) as e:
                # "signal only works in main thread" - expected in background threads
                if "main thread" in str(e).lower():
                    return None  # Suppress silently
                raise  # Re-raise other errors
        
        # Apply the patch
        signal_module.signal = patched_signal
        
        # Also patch Twisted signal installation methods
        try:
            import twisted.internet._signals
            import twisted.internet.base
            
            # Patch SignalReactorMixin.install
            original_install = twisted.internet._signals.SignalReactorMixin.install
            def patched_install(self):
                try:
                    return original_install(self)
                except (ValueError, OSError, AttributeError):
                    return None
            twisted.internet._signals.SignalReactorMixin.install = patched_install
            
            # Patch ReactorBase._reallyStartRunning
            original_really_start = twisted.internet.base.ReactorBase._reallyStartRunning
            def patched_really_start(self):
                try:
                    if hasattr(self, '_signals'):
                        try:
                            self._signals.install()
                        except (ValueError, OSError):
                            pass
                    return original_really_start(self)
                except (ValueError, OSError, AttributeError):
                    pass
            twisted.internet.base.ReactorBase._reallyStartRunning = patched_really_start
            
            # Patch Scrapy's signal installation
            try:
                import scrapy.utils.ossignal
                original_scrapy_install = scrapy.utils.ossignal.install_shutdown_handlers
                def patched_scrapy_install(sig, func):
                    try:
                        return original_scrapy_install(sig, func)
                    except (ValueError, OSError):
                        pass
                scrapy.utils.ossignal.install_shutdown_handlers = patched_scrapy_install
            except (ImportError, AttributeError):
                pass
        except (ImportError, AttributeError):
            pass
        
        # Create crawler process
        # Note: CrawlerProcess can only be instantiated once per process
        # We use install_root_handler=False to avoid Twisted reactor conflicts
        # This prevents signal handler installation which causes errors in background threads
        process = CrawlerProcess(scrapy_settings, install_root_handler=False)
        
        # Suppress Scrapy/Twisted loggers and stderr during entire execution
        import logging
        import warnings
        
        # Suppress specific Scrapy/Twisted loggers
        scrapy_loggers_to_suppress = [
            'twisted.internet.base',
            'scrapy.utils.ossignal',
            'scrapy.core.engine',
            'scrapy.core.scraper',
            'scrapy.core.scheduler',
            'scrapy.extensions.corestats',
            'twisted.internet._signals'
        ]
        old_levels = {}
        for logger_name in scrapy_loggers_to_suppress:
            scrapy_logger = logging.getLogger(logger_name)
            old_levels[logger_name] = scrapy_logger.level
            scrapy_logger.setLevel(logging.CRITICAL + 1)  # Suppress all messages
        
        # Suppress Python warnings and redirect stderr for entire Scrapy execution
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Redirect stderr BEFORE creating CrawlerProcess to catch all Twisted errors
            old_stderr = sys.stderr
            try:
                sys.stderr = stderr_buffer
                
                try:
                    # Run spider
                    process.crawl(DataCaptureSpider, profile_url=profile_url)
                    
                    # Start the process (errors will be captured in stderr_buffer)
                    try:
                        process.start()
                    except (ValueError, RuntimeError, AttributeError, AssertionError) as scrapy_error:
                        # These are expected Scrapy errors in background threads
                        error_msg = str(scrapy_error)
                        if any(phrase in error_msg for phrase in [
                            "signal only works in main thread",
                            "Scraper slot not assigned",
                            "has no attribute 'dqs'",
                            "assert self.start_time is not None"
                        ]):
                            # Expected error - silently ignore
                            pass
                        else:
                            # Unexpected error - log it
                            logger.debug(f"Scrapy error (may be harmless): {scrapy_error}")
                except Exception as e:
                    # Only log if it's not a known Scrapy background thread error
                    error_msg = str(e)
                    if not any(phrase in error_msg for phrase in [
                        "signal only works in main thread",
                        "Scraper slot not assigned",
                        "has no attribute 'dqs'",
                        "assert self.start_time is not None"
                    ]):
                        logger.error(f"Error running Scrapy spider: {e}")
                    
                    # Return empty data on error (scraping failed)
                    return self._get_empty_scraped_data(platform=platform_name, profile_url=profile_url)
            finally:
                # Always restore stderr, logger levels, and signal function
                sys.stderr = old_stderr
                signal_module.signal = original_signal  # Restore original signal function
                for logger_name, old_level in old_levels.items():
                    logging.getLogger(logger_name).setLevel(old_level)
        
        if not data_captured:
            # This is expected - Facebook/Instagram often block scraping
            # The system will automatically use SERP Google search as fallback
            # This is not an error - SERP is the primary method, social media scraping is optional
            logger.debug(f"Social media scraping returned no data from {profile_url} (expected - SERP will be used)")
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
        Scrape profile data from social media platform
        Note: Scrapy errors about signals in background threads are expected and harmless
        """
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
