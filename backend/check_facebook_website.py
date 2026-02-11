"""Check the website linked from Facebook page"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.content_scraper import ContentScraper
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def check_website():
    print("=" * 80)
    print("CHECKING BACOLODFOODHUNTERS.COM WEBSITE")
    print("=" * 80)
    
    # The Facebook page mentions bacolodfoodhunters.com
    url = "https://bacolodfoodhunters.com"
    
    print(f"\n[Scraping] {url}")
    
    scraper = ContentScraper()
    content = await scraper.scrape_url(url, "restaurants_food")
    
    if not content:
        print("❌ Failed to scrape")
        return
    
    print(f"\n✅ Scraped:")
    print(f"   Title: {content.get('title', 'N/A')}")
    print(f"   Content length: {len(content.get('content_text', ''))} chars")
    print(f"\n   Content preview:")
    print("   " + "="*76)
    preview = content.get('content_text', '')[:3000]
    for line in preview.split('\n')[:50]:
        if line.strip():
            print(f"   {line[:76]}")
    print("   " + "="*76)
    
    # Extract restaurants
    print(f"\n[Extracting restaurants...]")
    entities = await entity_extractor.extract_entities(content, "restaurants_food")
    
    print(f"\n✅ Extracted {len(entities)} restaurants")
    for i, entity in enumerate(entities, 1):
        name = entity.get("restaurant_name") or entity.get("name") or "Unknown"
        print(f"   {i}. {name}")
        if entity.get("address"):
            print(f"      Address: {entity.get('address')[:60]}")
        if entity.get("description"):
            print(f"      Description: {entity.get('description')[:100]}...")
    
    # Save to InstantDB
    if entities:
        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, restaurant in enumerate(entities):
            restaurant["category"] = "restaurants_food"
            restaurant_url = f"{url}#restaurant_{i}"
            saved = await instantdb_client.save_scraped_content(restaurant_url, restaurant)
            if saved:
                saved_count += 1
        
        print(f"\n✅ Saved {saved_count}/{len(entities)} restaurants to InstantDB")

if __name__ == "__main__":
    asyncio.run(check_website())
