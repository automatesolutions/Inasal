"""Rescrape Facebook page and extract restaurants from blog posts"""

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

async def rescrape_facebook():
    print("=" * 80)
    print("RESCRAPING FACEBOOK PAGE TO EXTRACT RESTAURANTS FROM BLOG POSTS")
    print("=" * 80)
    
    url = "https://www.facebook.com/BacolodFoodHunters/"
    
    print(f"\n[Scraping Facebook page] {url}")
    
    scraper = ContentScraper()
    content = await scraper.scrape_url(url, "restaurants_food")
    
    if not content:
        print("❌ Failed to scrape content")
        return
    
    print(f"\n✅ Scraped content:")
    print(f"   Title: {content.get('title', 'N/A')}")
    print(f"   Content length: {len(content.get('content_text', ''))} chars")
    print(f"\n   Content preview (first 2000 chars):")
    print("   " + "="*76)
    content_preview = content.get('content_text', '')[:2000]
    for line in content_preview.split('\n')[:30]:
        if line.strip():
            print(f"   {line[:76]}")
    print("   " + "="*76)
    
    # Extract restaurant entities with improved prompt
    print(f"\n[Extracting restaurant entities from blog posts with LLM...]")
    entities = await entity_extractor.extract_entities(content, "restaurants_food")
    
    print(f"\n✅ Extracted {len(entities)} restaurant entities")
    
    for i, entity in enumerate(entities, 1):
        name = entity.get("restaurant_name") or entity.get("name") or "Unknown"
        address = entity.get("address", "N/A")
        cuisine = entity.get("cuisine_type", "N/A")
        specialties = entity.get("specialties", [])
        desc = entity.get("description", "")[:150] if entity.get("description") else "N/A"
        
        print(f"\n   Entity {i}: {name}")
        if address and address != "N/A":
            print(f"      Address: {address[:80]}")
        if cuisine and cuisine != "N/A":
            print(f"      Cuisine: {cuisine}")
        if specialties:
            print(f"      Specialties: {specialties}")
        if desc and desc != "N/A":
            print(f"      Description: {desc}...")
    
    # Save to InstantDB
    if entities:
        print(f"\n[Saving {len(entities)} restaurants to InstantDB...]")
        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, restaurant in enumerate(entities):
            restaurant["category"] = "restaurants_food"
            restaurant_url = f"{url}#restaurant_{i}"
            saved = await instantdb_client.save_scraped_content(restaurant_url, restaurant)
            if saved:
                saved_count += 1
                name = restaurant.get("restaurant_name") or restaurant.get("name") or "Unknown"
                print(f"   ✅ Saved: {name}")
        
        print(f"\n✅ Successfully saved {saved_count}/{len(entities)} restaurants")
    
    # Verify
    print(f"\n[Verifying InstantDB...]")
    await asyncio.sleep(3)
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"\n✅ Total restaurants in InstantDB: {len(items)}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(rescrape_facebook())
