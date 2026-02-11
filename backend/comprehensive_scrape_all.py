"""
Comprehensive scraping script that scrapes ALL URLs from Google Sheet,
enriches with LLM, and saves to InstantDB. Retries until all URLs are successful.
"""

import asyncio
import sys
import codecs
import logging
from typing import Dict, List, Set
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from app.sheets_sync import fetch_and_parse_sheet
from app.content_scraper import ContentScraper
from app.instantdb_client import instantdb_client
from app.services.llm_enrichment import llm_enrichment_service

logger = logging.getLogger(__name__)

# Try to import ScrapyRunner, but handle if not available
try:
    from app.scrapers.scrapy_runner import ScrapyRunner
    SCRAPY_AVAILABLE = True
except ImportError:
    ScrapyRunner = None
    SCRAPY_AVAILABLE = False
    logger.warning("Scrapy not available, will use ContentScraper only")

MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds


async def scrape_with_retries(
    url: str,
    category: str,
    scraper: ContentScraper,
    scrapy_runner: ScrapyRunner,
    use_scrapy: bool,
    retry_count: int = 0
) -> Dict:
    """Scrape a URL with retries and LLM enrichment"""
    
    try:
        logger.info(f"[Attempt {retry_count + 1}/{MAX_RETRIES}] Scraping {category}: {url[:80]}...")
        
        # Scrape content
        if use_scrapy and scrapy_runner:
            content = await scrapy_runner.run_spider(url, category)
        else:
            content = await scraper.scrape_url(url, category)
        
        if content:
            # Ensure collection exists
            collection_name = instantdb_client._get_collection_for_category(category)
            await instantdb_client._ensure_collection_exists(collection_name)
            
            # Save to InstantDB
            saved = await instantdb_client.save_scraped_content(url, content)
            
            if saved:
                logger.info(f"✅ Successfully scraped and saved: {url[:80]}...")
                return {
                    "success": True,
                    "url": url,
                    "category": category,
                    "content": content
                }
            else:
                logger.error(f"❌ Failed to save to InstantDB: {url[:80]}...")
                return {
                    "success": False,
                    "url": url,
                    "category": category,
                    "error": "Failed to save to InstantDB"
                }
        else:
            logger.warning(f"⚠️  No content extracted: {url[:80]}...")
            return {
                "success": False,
                "url": url,
                "category": category,
                "error": "No content extracted"
            }
            
    except Exception as e:
        logger.error(f"❌ Error scraping {url[:80]}...: {e}")
        return {
            "success": False,
            "url": url,
            "category": category,
            "error": str(e)
        }


async def comprehensive_scrape():
    """Scrape all URLs from Google Sheet with retries until all succeed"""
    
    print("=" * 80)
    print("COMPREHENSIVE SCRAPING - ALL URLs FROM GOOGLE SHEET")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Fetch all URLs from Google Sheet")
    print("  2. Scrape each URL using Bright Data Web Unlocker")
    print("  3. Enrich with LLM to extract structured data")
    print("  4. Save to InstantDB category collections")
    print("  5. Retry failed URLs until all succeed")
    print("\n" + "=" * 80)
    
    # Initialize scrapers
    scraper = ContentScraper()
    scrapy_runner = ScrapyRunner() if SCRAPY_AVAILABLE else None
    scrapy_available = SCRAPY_AVAILABLE
    
    # Fetch URLs from sheet
    print("\n[Step 1] Fetching URLs from Google Sheet...")
    categories = await fetch_and_parse_sheet()
    
    if not categories:
        print("❌ No categories found in Google Sheet")
        return
    
    # Build URL list with categories
    all_urls = []
    for category, urls in categories.items():
        for url in urls:
            all_urls.append({
                "url": url,
                "category": category
            })
    
    total_urls = len(all_urls)
    print(f"   Found {total_urls} URLs across {len(categories)} categories")
    for cat, urls in categories.items():
        print(f"      {cat}: {len(urls)} URLs")
    
    # Check which URLs are already scraped
    print("\n[Step 2] Checking existing scraped content...")
    existing_scraped = await instantdb_client.get_all_scraped_content()
    existing_urls = set()
    for items in existing_scraped.values():
        for item in items:
            existing_urls.add(item.get("url"))
    
    # Filter out already scraped URLs
    urls_to_scrape = [u for u in all_urls if u["url"] not in existing_urls]
    
    if existing_urls:
        print(f"   Already scraped: {len(existing_urls)} URLs")
        print(f"   Need to scrape: {len(urls_to_scrape)} URLs")
    else:
        print(f"   No existing scraped content, will scrape all {total_urls} URLs")
        urls_to_scrape = all_urls
    
    if not urls_to_scrape:
        print("\n✅ All URLs already scraped!")
        return
    
    # Scrape with retries
    print(f"\n[Step 3] Scraping {len(urls_to_scrape)} URLs...")
    print("   Using Bright Data Web Unlocker for all URLs")
    print("   Applying LLM enrichment for structured data extraction")
    print("   Retrying failed URLs up to {MAX_RETRIES} times\n")
    
    results = []
    failed_urls = []
    
    # Determine which URLs should use Scrapy
    def should_use_scrapy(url: str) -> bool:
        scrapy_domains = [
            "tripadvisor.com",
            "facebook.com",
            "instagram.com",
            "reddit.com",
            "abs-cbn.com",
            "mb.com.ph",
            "philstar.com",
            "rappler.com",
            "inquirer.net",
        ]
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(sd in domain for sd in scrapy_domains)
    
    # First pass: scrape all URLs
    for i, url_info in enumerate(urls_to_scrape, 1):
        url = url_info["url"]
        category = url_info["category"]
        
        use_scrapy = scrapy_available and should_use_scrapy(url)
        
        result = await scrape_with_retries(
            url, category, scraper, scrapy_runner, use_scrapy, retry_count=0
        )
        
        results.append(result)
        
        if not result["success"]:
            failed_urls.append(url_info)
        
        # Progress update
        if i % 5 == 0 or i == len(urls_to_scrape):
            success_count = sum(1 for r in results if r["success"])
            print(f"   Progress: {i}/{len(urls_to_scrape)} URLs processed ({success_count} successful)")
        
        # Small delay to avoid overwhelming servers
        await asyncio.sleep(2)
    
    # Retry failed URLs
    retry_round = 1
    while failed_urls and retry_round < MAX_RETRIES:
        print(f"\n[Step 4.{retry_round}] Retrying {len(failed_urls)} failed URLs...")
        await asyncio.sleep(RETRY_DELAY)
        
        new_failed = []
        for url_info in failed_urls:
            url = url_info["url"]
            category = url_info["category"]
            use_scrapy = scrapy_available and should_use_scrapy(url)
            
            result = await scrape_with_retries(
                url, category, scraper, scrapy_runner, use_scrapy, retry_count=retry_round
            )
            
            # Update result
            for r in results:
                if r["url"] == url:
                    r.update(result)
                    break
            
            if not result["success"]:
                new_failed.append(url_info)
            
            await asyncio.sleep(2)
        
        failed_urls = new_failed
        retry_round += 1
    
    # Final summary
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\n✅ Successfully scraped: {len(successful)}/{len(results)} URLs")
    print(f"❌ Failed: {len(failed)}/{len(results)} URLs")
    
    if successful:
        print(f"\n✅ Successful by category:")
        by_category = {}
        for r in successful:
            cat = r["category"]
            by_category.setdefault(cat, 0)
            by_category[cat] += 1
        for cat, count in sorted(by_category.items()):
            print(f"      {cat}: {count} items")
    
    if failed:
        print(f"\n❌ Failed URLs:")
        for r in failed[:10]:  # Show first 10
            print(f"      {r['category']}: {r['url'][:80]}...")
            if r.get('error'):
                print(f"         Error: {r['error']}")
        if len(failed) > 10:
            print(f"      ... and {len(failed) - 10} more")
    
    # Verify in InstantDB
    print("\n[Step 5] Verifying data in InstantDB...")
    await asyncio.sleep(5)  # Wait for propagation
    
    all_scraped = await instantdb_client.get_all_scraped_content()
    total_items = sum(len(items) for items in all_scraped.values())
    
    print(f"\n   Total items in InstantDB: {total_items}")
    print(f"   Categories with data:")
    for cat, items in sorted(all_scraped.items()):
        print(f"      {cat}: {len(items)} items")
    
    # Check expected categories
    expected_categories = [
        "accommodation_hotels",
        "tourist_spots",
        "restaurants_food",
        "dangerous_areas",
        "scams",
        "secret_places"
    ]
    
    print(f"\n   Expected categories status:")
    for cat in expected_categories:
        count = len(all_scraped.get(cat, []))
        status = "✅" if count > 0 else "❌"
        print(f"      {status} {cat}: {count} items")
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SCRAPING COMPLETE")
    print("=" * 80)
    
    if failed:
        print(f"\n⚠️  Note: {len(failed)} URLs failed after {MAX_RETRIES} retries.")
        print("   These may require manual review or different scraping approaches.")
        print("   Check logs for specific error messages.")


if __name__ == "__main__":
    asyncio.run(comprehensive_scrape())
