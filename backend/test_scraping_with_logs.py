"""Test scraping with detailed logging"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def test_scraping():
    print("=" * 80)
    print("TESTING SCRAPING WITH DETAILED LOGGING")
    print("=" * 80)
    
    # Fetch sheet
    print("\n[Step 1] Fetching Google Sheet...")
    categories = await fetch_and_parse_sheet()
    print(f"   Found {len(categories)} categories")
    for cat, urls in categories.items():
        print(f"      {cat}: {len(urls)} URLs")
    
    # Scrape just one URL to test
    if categories:
        first_cat = list(categories.keys())[0]
        first_url = categories[first_cat][0] if categories[first_cat] else None
        
        if first_url:
            print(f"\n[Step 2] Testing scrape of single URL...")
            print(f"   Category: {first_cat}")
            print(f"   URL: {first_url}")
            
            # Use the scraping function directly
            test_categories = {first_cat: [first_url]}
            results = await scrape_all_urls_from_sheet(test_categories, max_concurrent=1)
            
            print(f"\n[Step 3] Scraping results:")
            for cat, items in results.items():
                print(f"   {cat}: {len(items)} items scraped")
                if items:
                    item = items[0]
                    print(f"      Sample item:")
                    print(f"         URL: {item.get('url', 'N/A')[:80]}")
                    print(f"         Title: {item.get('title', 'N/A')[:80]}")
                    print(f"         Has Description: {bool(item.get('description'))}")
                    print(f"         Has Images: {len(item.get('images', [])) > 0}")
            
            # Wait and check InstantDB
            print(f"\n[Step 4] Checking InstantDB after scraping...")
            await asyncio.sleep(3)
            
            items = await instantdb_client.get_scraped_content_by_category(first_cat)
            print(f"   Found {len(items)} items in InstantDB for category '{first_cat}'")
            
            if items:
                sample = items[0]
                print(f"   Sample from DB:")
                print(f"      ID: {sample.get('id')}")
                print(f"      URL: {sample.get('url', 'N/A')[:80]}")
                print(f"      Title: {sample.get('title', 'N/A')[:80]}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_scraping())
