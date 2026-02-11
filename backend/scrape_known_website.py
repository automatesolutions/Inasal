"""Scrape the known website from Facebook page"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.content_scraper import ContentScraper
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def scrape_website():
    print("=" * 80)
    print("SCRAPING BACOLODFOODHUNTERS.COM WEBSITE")
    print("=" * 80)
    print("\nThis website is linked from the Facebook page")
    print("and contains detailed restaurant reviews.\n")
    
    url = "https://bacolodfoodhunters.com"
    
    scraper = ContentScraper()
    print(f"[Scraping] {url}")
    
    content = await scraper.scrape_url(url, "restaurants_food")
    
    if not content:
        print("❌ Failed to scrape")
        return
    
    print(f"✅ Scraped {len(content.get('content_text', ''))} chars")
    print(f"   Title: {content.get('title', 'N/A')}")
    
    # Extract restaurants
    print(f"\n[Extracting restaurants with LLM...]")
    entities = await entity_extractor.extract_entities(content, "restaurants_food")
    
    print(f"✅ Extracted {len(entities)} restaurants\n")
    
    for i, entity in enumerate(entities, 1):
        name = entity.get("restaurant_name") or entity.get("name") or "Unknown"
        address = entity.get("address", "")
        cuisine = entity.get("cuisine_type", "")
        specialties = entity.get("specialties", [])
        desc = entity.get("description", "")[:100] if entity.get("description") else ""
        
        print(f"   {i}. {name}")
        if address:
            print(f"      📍 {address[:80]}")
        if cuisine:
            print(f"      🍽️  {cuisine}")
        if specialties:
            print(f"      ⭐ {', '.join(specialties[:3])}")
        if desc:
            print(f"      📝 {desc}...")
        print()
    
    # Save to InstantDB
    if entities:
        print(f"[Saving {len(entities)} restaurants to InstantDB...]")
        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, restaurant in enumerate(entities):
            restaurant["category"] = "restaurants_food"
            restaurant_url = f"{url}#restaurant_{i}"
            saved = await instantdb_client.save_scraped_content(restaurant_url, restaurant)
            if saved:
                saved_count += 1
        
        print(f"✅ Saved {saved_count}/{len(entities)} restaurants")
    
    # Verify
    await asyncio.sleep(3)
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"\n✅ Total restaurants in InstantDB: {len(items)}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(scrape_website())
