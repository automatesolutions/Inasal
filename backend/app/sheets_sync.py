"""
Google Sheets sync for Bacolod Details.
Fetches curated URLs from the sheet, checks that links work, then syncs to InstantDB.
Sheet: https://docs.google.com/spreadsheets/d/1tSFSpQ8IBBVIJrRUq0qXdVPUvDd-uqRuD3glYJNuhH4/edit?gid=0#gid=0
"""

import asyncio
import csv
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Timeout and concurrency for link checks (some sites block or are slow)
LINK_CHECK_TIMEOUT = 10.0
LINK_CHECK_CONCURRENCY = 5
USER_AGENT = "Mozilla/5.0 (compatible; BacolodTourist/1.0; +https://github.com/bacolod-tourist)"

SHEET_ID = "1tSFSpQ8IBBVIJrRUq0qXdVPUvDd-uqRuD3glYJNuhH4"
SHEET_GID = "0"
CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# Section headers in column A (as they appear in the sheet) -> internal category slug
CATEGORY_HEADERS = {
    "accommodation and hotels": "accommodation_hotels",
    "accomodation and hotels": "accommodation_hotels",  # typo in sheet
    "tourist spots & hidden gems": "tourist_spots",
    "tourist spots and hidden gems": "tourist_spots",
    "restaurants & food": "restaurants_food",
    "restaurants and food": "restaurants_food",
    "dangerous areas & travel warnings": "dangerous_areas",
    "dangerous areas and travel warnings": "dangerous_areas",
    "scams to watch out for": "scams",
    "secret places in bacolod": "secret_places",
}


def _normalize_header(cell: str) -> Optional[str]:
    """Match cell to a category slug."""
    if not cell or not isinstance(cell, str):
        return None
    # Normalize: strip, lowercase, and collapse multiple spaces
    key = " ".join(cell.strip().lower().split())
    
    # Direct match first
    if key in CATEGORY_HEADERS:
        return CATEGORY_HEADERS[key]
    
    # Fuzzy match for accommodation (handle typos and spacing variations)
    if "accommodation" in key or "accomodation" in key:
        if "hotel" in key:
            return "accommodation_hotels"
    
    # Fuzzy match for other categories
    if "tourist" in key and ("spot" in key or "gem" in key):
        return "tourist_spots"
    if "restaurant" in key and "food" in key:
        return "restaurants_food"
    if "dangerous" in key or "travel warning" in key:
        return "dangerous_areas"
    if "scam" in key:
        return "scams"
    if "secret" in key or "hidden" in key:
        return "secret_places"
    
    return None


def _is_url(cell: str) -> bool:
    if not cell or not isinstance(cell, str):
        return False
    s = cell.strip()
    return s.startswith("http://") or s.startswith("https://")


async def fetch_sheet_csv() -> str:
    """Fetch the Google Sheet as CSV (sheet must be shared as 'Anyone with link can view')."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(CSV_EXPORT_URL)
        response.raise_for_status()
        return response.text


def parse_sheet_csv(csv_text: str) -> Dict[str, List[str]]:
    """
    Parse CSV and return { category_slug: [url1, url2, ...] }.
    Column A: section headers or URLs.
    """
    categories: Dict[str, List[str]] = {}
    current_category: Optional[str] = None

    reader = csv.reader(csv_text.splitlines())
    for row in reader:
        if not row:
            continue
        cell = (row[0] or "").strip()
        if not cell:
            continue
        
        # CRITICAL FIX: Check if it's a URL FIRST before checking for category header
        # This prevents URLs containing keywords (like "tourist-spots-in-bacolod") 
        # from being incorrectly identified as category headers
        if _is_url(cell):
            if current_category:
                categories.setdefault(current_category, []).append(cell)
            continue
        
        # Only check for category header if it's NOT a URL
        slug = _normalize_header(cell)
        if slug:
            current_category = slug
            categories.setdefault(slug, [])

    return categories


def content_hash(categories: Dict[str, List[str]]) -> str:
    """Hash of current content for change detection."""
    content = "\n".join(f"{k}:{','.join(sorted(v))}" for k in sorted(categories) for v in [categories[k]])
    return hashlib.sha256(content.encode()).hexdigest()


async def _check_one_url(client: httpx.AsyncClient, url: str) -> Tuple[str, bool, Optional[int]]:
    """
    Check if a URL is reachable. Returns (url, ok, status_code).
    ok = True for 2xx/3xx, False for 4xx/5xx/timeout/error.
    """
    try:
        r = await client.head(
            url,
            timeout=LINK_CHECK_TIMEOUT,
            follow_redirects=True,
        )
        ok = 200 <= r.status_code < 400
        return (url, ok, r.status_code)
    except Exception as e:
        # Many sites reject HEAD; try GET with stream (read nothing)
        try:
            r = await client.get(
                url,
                timeout=LINK_CHECK_TIMEOUT,
                follow_redirects=True,
            )
            ok = 200 <= r.status_code < 400
            return (url, ok, r.status_code)
        except Exception as e2:
            logger.debug(f"Link check failed for {url[:60]}...: {e2}")
            return (url, False, None)


async def check_urls_from_sheet(categories: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Validate each URL from the parsed sheet.
    Returns (valid_categories, broken_by_category).
    valid_categories: only URLs that returned 2xx/3xx are kept.
    broken_by_category: list of URLs that failed (4xx, 5xx, timeout, error) per category.
    """
    valid: Dict[str, List[str]] = {}
    broken: Dict[str, List[str]] = {}

    async with httpx.AsyncClient(
        timeout=LINK_CHECK_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for slug, urls in categories.items():
            if not urls:
                valid[slug] = []
                broken[slug] = []
                continue
            # Check in batches to limit concurrency
            sem = asyncio.Semaphore(LINK_CHECK_CONCURRENCY)

            async def check_with_sem(u: str):
                async with sem:
                    return await _check_one_url(client, u)

            results = await asyncio.gather(*[check_with_sem(u) for u in urls])
            valid_urls = [u for u, ok, _ in results if ok]
            broken_urls = [u for u, ok, _ in results if not ok]
            valid[slug] = valid_urls
            broken[slug] = broken_urls
            if broken_urls:
                for u in broken_urls:
                    logger.warning(f"Broken link in sheet [{slug}]: {u[:80]}...")

    return valid, broken


async def fetch_and_parse_sheet() -> Dict[str, List[str]]:
    """Fetch sheet and return parsed categories -> URLs."""
    try:
        csv_text = await fetch_sheet_csv()
        return parse_sheet_csv(csv_text)
    except Exception as e:
        logger.error(f"Failed to fetch/parse Google Sheet: {e}")
        return {}


def _should_use_scrapy(url: str) -> bool:
    """
    Determine if URL should use Scrapy spider or ContentScraper.
    Returns True for complex sites that benefit from Scrapy, False for simple sites.
    """
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    
    # Sites that should use Scrapy
    scrapy_domains = [
        "tripadvisor",
        "facebook.com",
        "fb.com",
        "philippineshiddengems.com",
        "lakbaypinas.com",
        "thepinaysolobackpacker.com",
        "gmanetwork.com",
        "abs-cbn.com",
        "mb.com.ph",
        "philstar.com",
        "rappler.com",
        "inquirer.net",
    ]
    
    return any(sd in domain for sd in scrapy_domains)


async def scrape_all_urls_from_sheet(
    categories: Dict[str, List[str]], max_concurrent: int = 5
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape all URLs from parsed sheet categories using smart router.
    Routes URLs to Scrapy spiders for complex sites, ContentScraper for simple sites.
    Returns { category_slug: [scraped_content_dict, ...] }.
    """
    from app.content_scraper import ContentScraper
    from app.instantdb_client import instantdb_client
    
    # Try to import ScrapyRunner, but fall back to ContentScraper only if not available
    try:
        from app.scrapers.scrapy_runner import ScrapyRunner
        scrapy_runner = ScrapyRunner()
        scrapy_available = True
    except ImportError:
        logger.warning("Scrapy not available, using ContentScraper only")
        scrapy_runner = None
        scrapy_available = False
    
    content_scraper = ContentScraper()
    scraped_by_category: Dict[str, List[Dict[str, Any]]] = {}
    sem = asyncio.Semaphore(max_concurrent)
    
    total_urls = sum(len(urls) for urls in categories.values())
    logger.info(f"Starting to scrape {total_urls} URLs across {len(categories)} categories...")
    
    async def scrape_one(url: str, category: str, url_num: int):
        async with sem:
            try:
                logger.debug(f"[{url_num}/{total_urls}] Scraping {category}: {url[:60]}...")
                
                # Check if URL already exists in InstantDB (duplicate detection)
                already_scraped = await instantdb_client.url_already_scraped(url, category)
                if already_scraped:
                    logger.info(f"⏭️  Skipping {url[:60]}... (already scraped for {category})")
                    scraped_by_category.setdefault(category, []).append({
                        "url": url,
                        "status": "skipped",
                        "reason": "already_scraped"
                    })
                    return
                
                # Smart router: choose scraper based on URL
                use_scrapy = scrapy_available and _should_use_scrapy(url)
                
                if use_scrapy and scrapy_runner:
                    logger.debug(f"Using Scrapy spider for {url[:60]}...")
                    content = await scrapy_runner.run_spider(url, category)
                else:
                    logger.debug(f"Using ContentScraper for {url[:60]}...")
                    content = await content_scraper.scrape_url(url, category)
                
                if content:
                    # Check if content has website links (e.g., from Facebook pages)
                    website_links = content.get("website_links", [])
                    if website_links:
                        logger.info(f"🔗 Found {len(website_links)} website links on {url[:60]}...")
                        # Scrape website links too (they often have more restaurant content)
                        for website_url in website_links[:3]:  # Limit to first 3 links
                            try:
                                logger.info(f"   📄 Scraping linked website: {website_url[:60]}...")
                                website_content = await content_scraper.scrape_url(website_url, category)
                                if website_content:
                                    # Extract entities from website content
                                    try:
                                        from app.services.entity_extractor import entity_extractor
                                        website_entities = await entity_extractor.extract_entities(website_content, category)
                                        logger.info(f"   📦 Extracted {len(website_entities)} entities from {website_url[:60]}...")
                                        
                                        # Merge website entities into main entities list
                                        if 'entities' not in locals():
                                            entities = []
                                        entities.extend(website_entities)
                                    except Exception as e:
                                        logger.warning(f"   ⚠️  Entity extraction from website failed: {e}")
                            except Exception as e:
                                logger.warning(f"   ⚠️  Failed to scrape website link {website_url[:60]}...: {e}")
                    
                    # Extract multiple entities from content using LLM
                    try:
                        from app.services.entity_extractor import entity_extractor
                        page_entities = await entity_extractor.extract_entities(content, category)
                        logger.info(f"📦 Extracted {len(page_entities)} entities from {url[:60]}...")
                        
                        # Combine with website entities if any
                        if 'entities' in locals():
                            entities.extend(page_entities)
                        else:
                            entities = page_entities
                    except Exception as e:
                        logger.warning(f"Entity extraction failed, using single entity: {e}")
                        entities = [content]  # Fallback to single entity
                    
                    # Ensure collection exists before saving
                    collection_name = instantdb_client._get_collection_for_category(category)
                    await instantdb_client._ensure_collection_exists(collection_name)
                    
                    # Save each entity as a separate record
                    saved_count = 0
                    for i, entity in enumerate(entities):
                        # Ensure category is set for each entity
                        if not isinstance(entity, dict):
                            entity = {"description": str(entity)}
                        entity["category"] = category  # Explicitly set category
                        
                        # Create unique ID for each entity (combine URL hash with entity index)
                        import hashlib
                        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                        entity_id = f"{url_hash}-{i:04d}"
                        
                        # Add entity index to URL for uniqueness
                        entity_url = f"{url}#entity_{i}" if len(entities) > 1 else url
                        
                        logger.info(f"💾 Saving entity {i+1}/{len(entities)} from {url[:60]}... (category: {category})")
                        saved = await instantdb_client.save_scraped_content(entity_url, entity)
                        if saved:
                            saved_count += 1
                    
                    if saved_count > 0:
                        logger.info(f"✅ Successfully saved {saved_count}/{len(entities)} entities from {url[:60]}...")
                    else:
                        logger.error(f"❌ Failed to save entities from {url[:60]}...")
                    
                    return content
                else:
                    logger.warning(f"⚠️  No content extracted from {url[:60]}...")
                    return None
            except Exception as e:
                logger.warning(f"❌ Scraping failed for {url[:60]}...: {e}")
                return None
    
    # Scrape all URLs
    tasks = []
    url_num = 0
    for category, urls in categories.items():
        scraped_by_category[category] = []
        for url in urls:
            url_num += 1
            tasks.append(scrape_one(url, category, url_num))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Group results by category
    idx = 0
    for category, urls in categories.items():
        for url in urls:
            result = results[idx]
            idx += 1
            if isinstance(result, dict) and result:
                scraped_by_category[category].append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Exception scraping {url[:60]}...: {result}")
    
    total_scraped = sum(len(v) for v in scraped_by_category.values())
    logger.info(f"✅ Completed scraping: {total_scraped}/{total_urls} URLs successfully scraped")
    
    return scraped_by_category
