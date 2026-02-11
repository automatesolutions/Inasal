"""
Final scrape of remaining URLs - specifically Facebook and Reddit URLs
using Bright Data Web Unlocker with extended wait times
"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from app.bright_data_client import bright_data_client
from app.content_scraper import ContentScraper
from app.instantdb_client import instantdb_client
from app.services.llm_enrichment import llm_enrichment_service

logger = logging.getLogger(__name__)

# Remaining URLs that need special handling
REMAINING_URLS = [
    {"url": "https://www.reddit.com/r/Bacolod/comments/1g679wn/best_hidden_gem_in_bacolod/", "category": "tourist_spots"},
    {"url": "https://www.klook.com/en-PH/destination/c480-bacolod/1-things-to-do/", "category": "tourist_spots"},
    {"url": "https://www.facebook.com/BacolodFoodHunters/posts/bacolod-has-lots-of-cool-secret-places-and-one-of-them-is-commis-co-its-right-ne/1194224915395099/", "category": "tourist_spots"},
    {"url": "https://www.facebook.com/BacolodFoodHunters/", "category": "restaurants_food"},
    {"url": "https://www.reddit.com/r/Bacolod/comments/1qx4vsw/car_scams_in_bacolod_daw_damo_gaka_biktima_lately/", "category": "scams"},
    {"url": "https://www.facebook.com/CLIFFMotors/", "category": "scams"},
    {"url": "https://www.facebook.com/ELGonsSecretGarden/", "category": "secret_places"},
    {"url": "https://www.facebook.com/BacolodFoodHunters/posts/bacolod-has-lots-of-cool-secret-places-and-one-of-them-is-commis-co-its-right-ne/1194224915395099/", "category": "secret_places"},
]

async def scrape_with_bright_data_web_unlocker(url: str, category: str):
    """Force use Bright Data Web Unlocker with extended wait times"""
    logger.info(f"🌐 Using Bright Data Web Unlocker for {url[:80]}...")
    
    # Try Bright Data Web Unlocker with extended wait time
    html = await bright_data_client.scrape_with_web_unlocker(
        url, 
        wait_for=10000,  # 10 seconds for JS-heavy sites
        render=True
    )
    
    if html:
        logger.info(f"✅ Got HTML from Bright Data Web Unlocker ({len(html)} chars)")
        
        # Extract content
        scraper = ContentScraper()
        content = scraper._extract_content(html, url, category)
        
        if content:
            # Enrich with LLM
            try:
                content = await llm_enrichment_service.enrich_content(content, category)
            except Exception as e:
                logger.warning(f"LLM enrichment failed: {e}")
            
            # Ensure collection exists
            collection_name = instantdb_client._get_collection_for_category(category)
            await instantdb_client._ensure_collection_exists(collection_name)
            
            # Save to InstantDB
            saved = await instantdb_client.save_scraped_content(url, content)
            
            if saved:
                logger.info(f"✅ Successfully saved: {url[:80]}...")
                return True
            else:
                logger.error(f"❌ Failed to save: {url[:80]}...")
                return False
        else:
            logger.warning(f"⚠️  No content extracted from HTML")
            return False
    else:
        logger.warning(f"⚠️  Bright Data Web Unlocker returned no HTML")
        return False


async def main():
    print("=" * 80)
    print("FINAL SCRAPE - REMAINING URLS WITH BRIGHT DATA WEB UNLOCKER")
    print("=" * 80)
    
    if not bright_data_client._api_key:
        print("❌ Bright Data API key not configured")
        return
    
    print(f"\nScraping {len(REMAINING_URLS)} remaining URLs...")
    print("Using Bright Data Web Unlocker with extended wait times (10 seconds)\n")
    
    successful = []
    failed = []
    
    for i, url_info in enumerate(REMAINING_URLS, 1):
        url = url_info["url"]
        category = url_info["category"]
        
        print(f"[{i}/{len(REMAINING_URLS)}] {category}: {url[:80]}...")
        
        success = await scrape_with_bright_data_web_unlocker(url, category)
        
        if success:
            successful.append(url_info)
        else:
            failed.append(url_info)
        
        await asyncio.sleep(5)  # Delay between requests
    
    print("\n" + "=" * 80)
    print("FINAL SCRAPE COMPLETE")
    print("=" * 80)
    print(f"\n✅ Successful: {len(successful)}/{len(REMAINING_URLS)}")
    print(f"❌ Failed: {len(failed)}/{len(REMAINING_URLS)}")
    
    if failed:
        print(f"\nFailed URLs:")
        for f in failed:
            print(f"   {f['category']}: {f['url']}")
        print("\nNote: Facebook and Reddit URLs may require:")
        print("  - Bright Data Facebook/Reddit datasets (not web scraping)")
        print("  - Authentication tokens")
        print("  - Different scraping approaches")


if __name__ == "__main__":
    asyncio.run(main())
