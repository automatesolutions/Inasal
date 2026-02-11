"""Force rescrape restaurant URLs with improved entity extraction"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet
from app.content_scraper import ContentScraper
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def force_rescrape_restaurants():
    print("=" * 80)
    print("FORCE RESCRAPE RESTAURANTS WITH IMPROVED EXTRACTION")
    print("=" * 80)
    
    # Get URLs
    categories = await fetch_and_parse_sheet()
    restaurant_urls = categories.get("restaurants_food", [])
    
    print(f"\nFound {len(restaurant_urls)} restaurant URLs")
    for url in restaurant_urls:
        print(f"  - {url}")
    
    if not restaurant_urls:
        print("\n❌ No restaurant URLs found!")
        return
    
    scraper = ContentScraper()
    
    # Scrape each URL and extract ALL restaurants
    for url in restaurant_urls:
        if "facebook.com" in url.lower():
            print(f"\n⚠️  Skipping Facebook URL: {url}")
            continue
        
        print(f"\n[Scraping] {url}")
        content = await scraper.scrape_url(url, "restaurants_food")
        
        if not content:
            print("   ❌ Failed to scrape")
            continue
        
        print(f"   ✅ Scraped {len(content.get('content_text', ''))} chars")
        
        # Extract entities with improved prompt
        print(f"   [Extracting entities...]")
        entities = await entity_extractor.extract_entities(content, "restaurants_food")
        
        print(f"   ✅ Extracted {len(entities)} restaurant entities")
        
        for i, entity in enumerate(entities, 1):
            name = entity.get("restaurant_name") or entity.get("name") or "Unknown"
            print(f"      {i}. {name}")
            if entity.get("address"):
                print(f"         Address: {entity.get('address')[:60]}")
            if entity.get("cuisine_type"):
                print(f"         Cuisine: {entity.get('cuisine_type')}")
        
        # Save each entity
        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, entity in enumerate(entities):
            entity_url = f"{url}#entity_{i}" if len(entities) > 1 else url
            saved = await instantdb_client.save_scraped_content(entity_url, entity)
            if saved:
                saved_count += 1
        
        print(f"   ✅ Saved {saved_count}/{len(entities)} entities to InstantDB")
    
    # Verify
    print("\n[Verifying InstantDB...]")
    await asyncio.sleep(3)
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"\n✅ Total restaurant entities in InstantDB: {len(items)}")
    
    for i, item in enumerate(items[:10], 1):
        name = item.get("restaurant_name") or item.get("name") or item.get("title") or "Unknown"
        print(f"   {i}. {name}")
        if item.get("address"):
            print(f"      Address: {item.get('address')[:60]}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(force_rescrape_restaurants())
