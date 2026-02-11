"""Check detailed scraping status and identify failed URLs"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet
from app.instantdb_client import instantdb_client

async def check_status():
    print("=" * 80)
    print("DETAILED SCRAPING STATUS CHECK")
    print("=" * 80)
    
    # Get URLs from sheet
    print("\n[Step 1] Fetching URLs from Google Sheet...")
    categories = await fetch_and_parse_sheet()
    
    print(f"\n   Categories found: {len(categories)}")
    for cat, urls in categories.items():
        print(f"      {cat}: {len(urls)} URLs")
    
    # Check what's in InstantDB
    print("\n[Step 2] Checking scraped content in InstantDB...")
    all_scraped = await instantdb_client.get_all_scraped_content()
    
    print(f"\n   Scraped items by category:")
    total_scraped = 0
    for cat, items in all_scraped.items():
        print(f"      {cat}: {len(items)} items")
        total_scraped += len(items)
    
    # Compare URLs vs scraped
    print("\n[Step 3] Comparison: URLs vs Scraped Items")
    print(f"\n   {'Category':<30} {'URLs':<10} {'Scraped':<10} {'Status'}")
    print("   " + "-" * 60)
    
    expected_categories = [
        "accommodation_hotels",
        "tourist_spots",
        "restaurants_food",
        "dangerous_areas",
        "scams",
        "secret_places"
    ]
    
    for cat in expected_categories:
        urls_count = len(categories.get(cat, []))
        scraped_count = len(all_scraped.get(cat, []))
        status = "✅" if scraped_count > 0 else "❌"
        if urls_count > 0 and scraped_count == 0:
            status = "⚠️  (URLs exist but not scraped)"
        print(f"   {cat:<30} {urls_count:<10} {scraped_count:<10} {status}")
    
    print(f"\n   Total URLs: {sum(len(urls) for urls in categories.values())}")
    print(f"   Total Scraped: {total_scraped}")
    
    # Show URLs that haven't been scraped
    print("\n[Step 4] URLs not yet scraped:")
    for cat in expected_categories:
        urls = categories.get(cat, [])
        scraped_items = all_scraped.get(cat, [])
        scraped_urls = {item.get("url") for item in scraped_items}
        missing_urls = [url for url in urls if url not in scraped_urls]
        
        if missing_urls:
            print(f"\n   {cat} ({len(missing_urls)} URLs not scraped):")
            for url in missing_urls[:5]:  # Show first 5
                print(f"      - {url}")
            if len(missing_urls) > 5:
                print(f"      ... and {len(missing_urls) - 5} more")
    
    print("\n" + "=" * 80)
    print("STATUS CHECK COMPLETE")
    print("=" * 80)
    
    print("\nNote: Some URLs may fail to scrape due to:")
    print("  - Network timeouts")
    print("  - Sites blocking scrapers")
    print("  - Invalid or broken URLs")
    print("  - JavaScript-heavy sites requiring browser automation")

if __name__ == "__main__":
    asyncio.run(check_status())
