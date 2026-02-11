"""Test entity extraction - scrape one URL and extract multiple entities"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def test_extraction():
    print("=" * 80)
    print("TESTING ENTITY EXTRACTION")
    print("=" * 80)
    
    # Get URLs
    categories = await fetch_and_parse_sheet()
    
    # Test with tourist_spots (should have multiple attractions)
    if "tourist_spots" in categories and categories["tourist_spots"]:
        test_url = categories["tourist_spots"][0]
        print(f"\nTesting with URL: {test_url}")
        print(f"Category: tourist_spots")
        print(f"\nThis URL should extract multiple tourist spots as separate entities...")
        
        # Scrape with entity extraction
        test_categories = {"tourist_spots": [test_url]}
        results = await scrape_all_urls_from_sheet(test_categories, max_concurrent=1)
        
        # Check results
        print(f"\nScraping completed. Checking InstantDB...")
        await asyncio.sleep(3)
        
        items = await instantdb_client.get_scraped_content_by_category("tourist_spots")
        print(f"\nFound {len(items)} items in InstantDB for tourist_spots")
        
        # Show sample items
        for i, item in enumerate(items[:5], 1):
            print(f"\n  Item {i}:")
            print(f"    ID: {item.get('id')}")
            print(f"    Title/Name: {item.get('title') or item.get('name') or item.get('attraction_name')}")
            print(f"    Address: {item.get('address') or (item.get('location', {}).get('address') if isinstance(item.get('location'), dict) else 'N/A')}")
            print(f"    Description: {(item.get('description') or '')[:100]}...")
            print(f"    Images: {len(item.get('images', []))} images")
            if item.get('attraction_name'):
                print(f"    ✅ Has attraction_name field")
            if item.get('opening_hours'):
                print(f"    Opening Hours: {item.get('opening_hours')}")
            if item.get('entrance_fee'):
                print(f"    Entrance Fee: {item.get('entrance_fee')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_extraction())
