"""Final comprehensive scrape of all restaurant URLs including website links"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def final_scrape():
    print("=" * 80)
    print("FINAL COMPREHENSIVE RESTAURANT SCRAPING")
    print("=" * 80)
    print("\nThis will:")
    print("1. Fetch all restaurant URLs from Google Sheet")
    print("2. Scrape each URL with Bright Data Web Unlocker")
    print("3. Extract website links from Facebook pages")
    print("4. Scrape linked websites for more restaurant content")
    print("5. Use LLM to extract ALL restaurants mentioned")
    print("6. Save each restaurant as a separate entity to InstantDB")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    restaurant_urls = categories.get("restaurants_food", [])
    
    print(f"\n📋 Restaurant URLs from Google Sheet: {len(restaurant_urls)}")
    for i, url in enumerate(restaurant_urls, 1):
        print(f"   {i}. {url}")
    
    if not restaurant_urls:
        print("\n❌ No restaurant URLs found!")
        return
    
    # Scrape all URLs (this will also scrape website links found on pages)
    print(f"\n{'='*80}")
    print("SCRAPING ALL URLS...")
    print(f"{'='*80}\n")
    
    results = await scrape_all_urls_from_sheet(
        {"restaurants_food": restaurant_urls},
        max_concurrent=3
    )
    
    restaurant_results = results.get("restaurants_food", [])
    print(f"\n✅ Scraped {len(restaurant_results)} URLs successfully")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("VERIFYING INSTANTDB...")
    print(f"{'='*80}")
    await asyncio.sleep(5)  # Wait for propagation
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"\n✅ Total restaurants in InstantDB: {len(items)}")
    
    # Show unique restaurants
    unique_restaurants = {}
    for item in items:
        name = item.get("restaurant_name") or item.get("name") or item.get("title", "Unknown")
        if name and name != "Unknown" and "Bacolod Food Hunters" not in name:
            if name not in unique_restaurants:
                unique_restaurants[name] = item
    
    print(f"\n📊 Unique restaurants found: {len(unique_restaurants)}")
    print("\n📋 Restaurant List:")
    for i, (name, item) in enumerate(sorted(unique_restaurants.items())[:30], 1):
        print(f"\n   {i}. {name}")
        if item.get("address"):
            print(f"      📍 {item.get('address')[:80]}")
        if item.get("cuisine_type"):
            print(f"      🍽️  {item.get('cuisine_type')}")
        if item.get("specialties"):
            print(f"      ⭐ Specialties: {', '.join(item.get('specialties', [])[:3])}")
        if item.get("description"):
            desc = item.get("description", "")[:100]
            if desc:
                print(f"      📝 {desc}...")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"\n✅ All restaurant URLs have been scraped")
    print(f"✅ LLM has extracted restaurant entities")
    print(f"✅ {len(items)} total restaurant entities saved to InstantDB")
    print(f"✅ {len(unique_restaurants)} unique restaurants found")
    print("\nCheck InstantDB dashboard: scraped_content_restaurants_food collection")

if __name__ == "__main__":
    asyncio.run(final_scrape())
