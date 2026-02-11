"""Scrape the 2 restaurant URLs from Google Sheet"""

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

async def scrape_restaurants():
    print("=" * 80)
    print("SCRAPING RESTAURANTS & FOOD URLs FROM GOOGLE SHEET")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    restaurant_urls = categories.get("restaurants_food", [])
    
    if not restaurant_urls:
        print("\n❌ No restaurant URLs found in sheet!")
        return
    
    print(f"\n📋 Found {len(restaurant_urls)} restaurant URLs:")
    for i, url in enumerate(restaurant_urls, 1):
        print(f"   {i}. {url}")
    
    # Scrape each URL
    scraper = ContentScraper()
    all_restaurants = []
    
    for i, url in enumerate(restaurant_urls, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(restaurant_urls)}] Scraping: {url}")
        print(f"{'='*80}")
        
        try:
            content = await scraper.scrape_url(url, "restaurants_food")
            
            if not content:
                print(f"   ❌ Failed to scrape content")
                if "facebook.com" in url.lower():
                    print(f"   ⚠️  Facebook URLs are difficult to scrape - may need Bright Data Web Unlocker")
                continue
            
            print(f"   ✅ Scraped {len(content.get('content_text', ''))} chars")
            print(f"   Title: {content.get('title', 'N/A')[:80]}")
            
            # Extract restaurant entities using LLM
            print(f"\n   [Extracting restaurant entities with LLM...]")
            entities = await entity_extractor.extract_entities(content, "restaurants_food")
            
            print(f"   ✅ Extracted {len(entities)} restaurant entities")
            
            for j, entity in enumerate(entities, 1):
                name = entity.get("restaurant_name") or entity.get("name") or entity.get("title") or "Unknown"
                address = entity.get("address", "N/A")
                cuisine = entity.get("cuisine_type", "N/A")
                specialties = entity.get("specialties", [])
                
                print(f"\n      Entity {j}: {name}")
                if address and address != "N/A":
                    print(f"         Address: {address[:80]}")
                if cuisine and cuisine != "N/A":
                    print(f"         Cuisine: {cuisine}")
                if specialties:
                    print(f"         Specialties: {specialties}")
                if entity.get("opening_hours"):
                    print(f"         Hours: {entity.get('opening_hours')}")
            
            all_restaurants.extend(entities)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save all restaurants to InstantDB
    if all_restaurants:
        print(f"\n{'='*80}")
        print(f"[Saving {len(all_restaurants)} restaurants to InstantDB...]")
        print(f"{'='*80}")
        
        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, restaurant in enumerate(all_restaurants):
            restaurant["category"] = "restaurants_food"
            restaurant_url = f"{restaurant_urls[0] if restaurant_urls else 'unknown'}#restaurant_{i}"
            saved = await instantdb_client.save_scraped_content(restaurant_url, restaurant)
            if saved:
                saved_count += 1
                name = restaurant.get("restaurant_name") or restaurant.get("name") or "Unknown"
                print(f"   ✅ Saved: {name}")
        
        print(f"\n✅ Successfully saved {saved_count}/{len(all_restaurants)} restaurants")
    else:
        print("\n⚠️  No restaurants extracted from any URLs")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("[Verifying InstantDB...]")
    print(f"{'='*80}")
    await asyncio.sleep(3)
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"\n✅ Total restaurants in InstantDB: {len(items)}")
    
    if items:
        print("\n📋 Sample restaurants:")
        for i, item in enumerate(items[:15], 1):
            name = item.get("restaurant_name") or item.get("name") or item.get("title") or "Unknown"
            print(f"\n   {i}. {name}")
            if item.get("address"):
                print(f"      Address: {item.get('address')[:80]}")
            if item.get("cuisine_type"):
                print(f"      Cuisine: {item.get('cuisine_type')}")
            if item.get("specialties"):
                print(f"      Specialties: {item.get('specialties')}")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(scrape_restaurants())
