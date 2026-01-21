"""Custom Scrapy middleware for Bright Data Residential Proxy"""

import logging

logger = logging.getLogger(__name__)


class BrightDataProxyMiddleware:
    """Middleware to inject Bright Data Residential Proxy into requests"""
    
    def __init__(self):
        self.proxy_url = self._get_proxy_url()
    
    def _get_proxy_url(self):
        """Get Bright Data Residential Proxy URL"""
        try:
            from app.config import settings
            
            username = settings.bright_data_residential_username
            password = settings.bright_data_residential_password
            endpoint = settings.bright_data_residential_endpoint or "brd.superproxy.io:33335"
            
            if not username or not password:
                logger.warning("Bright Data Residential Proxy not fully configured (missing username or password)")
                return None
            
            # Format: http://{USERNAME}:{PASSWORD}@{ENDPOINT}
            proxy_url = f"http://{username}:{password}@{endpoint}"
            logger.info(f"Bright Data proxy configured: {proxy_url[:60]}...")
            return proxy_url
        except Exception as e:
            logger.error(f"Error getting Bright Data proxy URL: {e}")
            return None
    
    def process_request(self, request, spider):
        """Process request and add Bright Data proxy"""
        if self.proxy_url:
            request.meta['proxy'] = self.proxy_url
            spider.logger.debug(f"Using Bright Data proxy for {request.url}")
        else:
            spider.logger.warning("Bright Data proxy not configured, request will use direct connection")
        return None
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance from crawler"""
        return cls()
