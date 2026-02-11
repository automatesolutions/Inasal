"""Test duplicate detection and personality integration"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def test_duplicate_detection():
    print("=" * 80)
    print("TESTING DUPLICATE DETECTION")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    
    # Test with tourist_spots (should have URLs)
    tourist_urls = categories.get("tourist_spots", [])
    if not tourist_urls:
        print("\n❌ No tourist_spots URLs found in sheet")
        return
    
    test_url = tourist_urls[0]
    print(f"\n📋 Testing with URL: {test_url[:80]}...")
    
    # Check if already scraped
    print("\n1. Checking if URL already exists...")
    exists = await instantdb_client.url_already_scraped(test_url, "tourist_spots")
    print(f"   Result: {'✅ Already scraped' if exists else '❌ Not scraped yet'}")
    
    # Try scraping (should skip if duplicate)
    print("\n2. Attempting to scrape (should skip if duplicate)...")
    results = await scrape_all_urls_from_sheet(
        {"tourist_spots": [test_url]},
        max_concurrent=1
    )
    
    result = results.get("tourist_spots", [{}])[0] if results.get("tourist_spots") else {}
    status = result.get("status", "unknown")
    
    if status == "skipped":
        print(f"   ✅ Correctly skipped duplicate URL")
    elif status == "success":
        print(f"   ⚠️  Scraped URL (may be new or duplicate detection didn't work)")
    else:
        print(f"   Status: {status}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_duplicate_detection())
