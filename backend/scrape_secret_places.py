"""Scrape Secret Places URLs from Google Sheet with improved extraction"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def scrape_secret_places():
    print("=" * 80)
    print("SCRAPING SECRET PLACES IN BACOLOD")
    print("=" * 80)
    print("\nThis will:")
    print("1. Fetch all Secret Places URLs from Google Sheet")
    print("2. Scrape each URL with Bright Data Web Unlocker")
    print("3. Use LLM to extract ALL secret places mentioned")
    print("4. Save each secret place as a separate entity to InstantDB")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    secret_places_urls = categories.get("secret_places", [])
    
    print(f"\n📋 Secret Places URLs from Google Sheet: {len(secret_places_urls)}")
    for i, url in enumerate(secret_places_urls, 1):
        print(f"   {i}. {url[:80]}...")
    
    if not secret_places_urls:
        print("\n❌ No secret places URLs found!")
        return
    
    # Scrape all URLs
    print(f"\n{'='*80}")
    print("SCRAPING ALL SECRET PLACES URLS...")
    print(f"{'='*80}\n")
    
    results = await scrape_all_urls_from_sheet(
        {"secret_places": secret_places_urls},
        max_concurrent=3
    )
    
    secret_places_results = results.get("secret_places", [])
    print(f"\n✅ Scraped {len(secret_places_results)} URLs successfully")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("VERIFYING INSTANTDB...")
    print(f"{'='*80}")
    await asyncio.sleep(5)  # Wait for propagation
    
    items = await instantdb_client.get_scraped_content_by_category("secret_places")
    print(f"\n✅ Total secret places in InstantDB: {len(items)}")
    
    # Show unique secret places
    unique_places = {}
    for item in items:
        name = item.get("place_name") or item.get("name") or item.get("title", "Unknown")
        if name and name != "Unknown":
            if name not in unique_places:
                unique_places[name] = item
    
    print(f"\n📊 Unique secret places found: {len(unique_places)}")
    print("\n📋 Secret Places List:")
    for i, (name, item) in enumerate(sorted(unique_places.items())[:30], 1):
        print(f"\n   {i}. {name}")
        if item.get("address"):
            print(f"      📍 {item.get('address')[:80]}")
        if item.get("description"):
            desc = item.get("description", "")[:150]
            if desc:
                print(f"      📝 {desc}...")
        if item.get("why_secret"):
            print(f"      🔒 Why Secret: {item.get('why_secret')[:100]}...")
        if item.get("how_to_find"):
            print(f"      🗺️  How to Find: {item.get('how_to_find')[:100]}...")
        if item.get("tips"):
            tips = item.get("tips", [])
            if isinstance(tips, list) and tips:
                print(f"      💡 Tips: {', '.join(tips[:3])}")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"\n✅ All secret places URLs have been scraped")
    print(f"✅ LLM has extracted secret place entities")
    print(f"✅ {len(items)} total secret place entities saved to InstantDB")
    print(f"✅ {len(unique_places)} unique secret places found")
    print("\nCheck InstantDB dashboard: scraped_content_secret_places collection")

if __name__ == "__main__":
    asyncio.run(scrape_secret_places())
