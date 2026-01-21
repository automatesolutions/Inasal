# Scrapy + Bright Data Residential Proxy Setup Guide

## Overview

This implementation uses **Scrapy** (Python web scraping framework) with **Bright Data Residential Proxy** to scrape Facebook and Instagram profile data.

## Architecture

```
User Login → Background Job → Search Profiles (Bright Data Google Search)
                                    ↓
                            Find Profile URLs
                                    ↓
                            Scrape Profile Data (Scrapy + Bright Data Residential Proxy)
                                    ↓
                            Extract: bio, posts, interests, location
                                    ↓
                            LLM Analysis → Personality Traits
```

## Installation

1. **Install Scrapy dependencies:**

```bash
cd backend
poetry add scrapy scrapy-playwright
```

Or manually add to `pyproject.toml`:
```toml
scrapy = "^2.11.0"
scrapy-playwright = "^0.0.33"
```

2. **Configure Bright Data Residential Proxy:**

Add to `backend/.env`:

```env
# Bright Data API Configuration
BRIGHT_DATA_API_TOKEN=your_api_token_here
BRIGHT_DATA_ZONE=webscrape_amzn

# Bright Data Residential Proxy Configuration
BRIGHT_DATA_RESIDENTIAL_USERNAME=brd-customer-{CUSTOMER_ID}-zone-{ZONE_NAME}__proxy1
BRIGHT_DATA_RESIDENTIAL_PASSWORD=your_password_here
BRIGHT_DATA_RESIDENTIAL_ENDPOINT=brd.superproxy.io:33335
BRIGHT_DATA_PROXY_TYPE=auto
```

**Example Configuration (from your .env):**
```env
BRIGHT_DATA_API_TOKEN=eb2ca709644144656034d231530b20b5a27eff44306808843c78a12019fee95b
BRIGHT_DATA_ZONE=webscrape_amzn
BRIGHT_DATA_RESIDENTIAL_USERNAME=brd-customer-hl_c2b71bb6-zone-webscraperamzn__proxy1
BRIGHT_DATA_RESIDENTIAL_PASSWORD=89gz77iw6dtm
BRIGHT_DATA_RESIDENTIAL_ENDPOINT=brd.superproxy.io:33335
BRIGHT_DATA_PROXY_TYPE=auto
```

**How to get Bright Data credentials:**
1. Log into Bright Data dashboard
2. Go to **Proxies & Scraping Infrastructure** → **Residential Proxies**
3. Find your **Username** (format: `brd-customer-{CUSTOMER_ID}-zone-{ZONE_NAME}__proxy1`)
4. Get your **Password** (set in Bright Data dashboard)
5. Note your **Endpoint** (usually `brd.superproxy.io:33335`)

**Proxy URL Format:**
```
http://{BRIGHT_DATA_RESIDENTIAL_USERNAME}:{BRIGHT_DATA_RESIDENTIAL_PASSWORD}@{BRIGHT_DATA_RESIDENTIAL_ENDPOINT}
```

## Files Created

1. **`backend/app/scrapers/social_media_spider.py`**
   - `FacebookProfileSpider` - Scrapes Facebook profiles
   - `InstagramProfileSpider` - Scrapes Instagram profiles
   - Uses CSS selectors to extract: bio, posts, interests, location, profile picture

2. **`backend/app/scrapers/proxy_middleware.py`**
   - `BrightDataProxyMiddleware` - Injects Bright Data proxy into all Scrapy requests
   - Automatically configures proxy from settings

3. **`backend/app/scrapers/scrapy_settings.py`**
   - Scrapy configuration: delays, concurrency, user agents, etc.

4. **`backend/app/social_scraper.py`** (Updated)
   - `scrape_profile_data()` - Now uses Scrapy with Bright Data proxy
   - Runs spiders asynchronously using `asyncio.run_in_executor()`

## How It Works

### 1. Profile Search (Already Working)
```python
# Uses Bright Data Google Search API
facebook_results = await bright_data.search_public(
    source="google",
    query='"Juan Dela Cruz" site:facebook.com',
    limit=5
)
# Returns: [{"url": "https://facebook.com/juan.delacruz", ...}]
```

### 2. Profile Scraping (New - Scrapy + Bright Data Proxy)
```python
# Scrapy spider runs with Bright Data Residential Proxy
scraped_data = await scraper.scrape_profile_data(
    profile_url="https://facebook.com/juan.delacruz",
    platform="facebook"
)
# Returns: {
#   "bio": "Travel enthusiast...",
#   "posts_content": ["Post 1", "Post 2"],
#   "interests": ["travel", "food"],
#   "location": "Bacolod City"
# }
```

### 3. Scrapy Process Flow

1. **Spider Initialization:**
   - `FacebookProfileSpider` or `InstagramProfileSpider` is created
   - Profile URL is set as start URL

2. **Request Made:**
   - Scrapy makes HTTP request to profile URL
   - `BrightDataProxyMiddleware` intercepts request
   - Adds Bright Data proxy to `request.meta['proxy']`
   - Request goes through Bright Data Residential Proxy

3. **Response Parsed:**
   - Spider's `parse()` method extracts data using CSS selectors
   - Returns dictionary with scraped data

4. **Data Returned:**
   - Scraped data is captured and returned to `scrape_profile_data()`
   - Used by personality analysis pipeline

## CSS Selectors Used

### Facebook:
- **Bio:** `meta[property="og:description"]` or `div[data-testid="profile-bio"]`
- **Location:** `span[data-testid="profile-location"]` or `a[href*="/places/"]`
- **Profile Picture:** `meta[property="og:image"]` or `img[data-testid="profile-picture"]`
- **Posts:** `div[data-pagelet="FeedUnit"]` or `div[role="article"]`
- **Interests:** `a[href*="/pages/"]` or `a[href*="/groups/"]`

### Instagram:
- **Bio:** `meta[property="og:description"]`
- **Profile Picture:** `meta[property="og:image"]`
- **Posts:** `article img::attr(alt)` (captions)
- **Hashtags:** `a[href*="/explore/tags/"]`

## Testing

### Test Scrapy Spider Directly:

```python
from scrapy.crawler import CrawlerProcess
from app.scrapers.social_media_spider import FacebookProfileSpider

process = CrawlerProcess()
process.crawl(FacebookProfileSpider, profile_url="https://facebook.com/username")
process.start()
```

### Test Full Pipeline:

```python
from app.social_scraper import SocialMediaScraper

scraper = SocialMediaScraper()

# Search for profiles
results = await scraper.search_social_profiles("Juan", "Dela Cruz")

# Scrape first Facebook profile
if results["facebook_profiles"]:
    profile_url = results["facebook_profiles"][0]["url"]
    data = await scraper.scrape_profile_data(profile_url, "facebook")
    print(data)
```

## Troubleshooting

### Issue: "Bright Data proxy not configured"
**Solution:** Add `BRIGHT_DATA_CUSTOMER_ID`, `BRIGHT_DATA_RESIDENTIAL_ZONE`, and `BRIGHT_DATA_RESIDENTIAL_PASSWORD` to `.env`

### Issue: "Scrapy reactor already installed"
**Solution:** This happens if CrawlerProcess is instantiated multiple times. The current implementation handles this by running spiders in separate threads.

### Issue: "No data captured"
**Possible causes:**
1. Profile URL is incorrect or profile is private
2. CSS selectors need updating (Facebook/Instagram change their HTML structure)
3. Proxy is blocked or rate-limited
4. Profile requires authentication

### Issue: "Scrapy not installed"
**Solution:** Run `poetry install` or `poetry add scrapy`

## Notes

- **Scrapy is synchronous** but we run it in a thread executor to work with async code
- **Bright Data Residential Proxy** rotates IPs automatically
- **Rate limiting** is handled by Scrapy's `DOWNLOAD_DELAY` and `AUTOTHROTTLE`
- **Facebook/Instagram HTML changes** - CSS selectors may need updates if scraping fails
- **Private profiles** - Cannot scrape private profiles, will return empty data

## Next Steps

1. Install Scrapy: `poetry add scrapy scrapy-playwright`
2. Configure Bright Data Residential Proxy credentials in `.env`
3. Test with a public Facebook/Instagram profile
4. Monitor logs for scraping success/failures
5. Update CSS selectors if Facebook/Instagram changes their HTML structure
