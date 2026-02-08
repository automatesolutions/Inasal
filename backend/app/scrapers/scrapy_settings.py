"""Scrapy settings configuration for social media scraping"""

# Scrapy settings for social media scraping
BOT_NAME = 'social_scraper'

SPIDER_MODULES = ['app.scrapers']
NEWSPIDER_MODULE = 'app.scrapers'

# Enable proxy middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
    'app.scrapers.proxy_middleware.BrightDataProxyMiddleware': 100,  # Higher priority
}

# Obey robots.txt rules (set to False for social media)
ROBOTSTXT_OBEY = False

# Configure delays for requests
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# The download delay setting will honor only one of:
# Use CONCURRENT_REQUESTS_PER_DOMAIN only: DownloaderAwarePriorityQueue does not support CONCURRENT_REQUESTS_PER_IP
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Disable cookies (optional, can help avoid detection)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []

# Set settings whose default value is deprecated
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
