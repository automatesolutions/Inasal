"""Scrape accommodation URLs from Google Sheet"""

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

async def scrape_accommodation():
    print("=" * 80)
    print("SCRAPING ACCOMMODATION & HOTELS URLs FROM GOOGLE SHEET")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    
    # Check all possible category names
    accommodation_urls = []
    for key in categories.keys():
        if "accommodation" in key.lower() or "hotel" in key.lower() or "accomodation" in key.lower():
            accommodation_urls = categories[key]
            print(f"\n✅ Found category: '{key}' with {len(accommodation_urls)} URLs")
            break
    
    if not accommodation_urls:
        print("\n⚠️  Checking all categories...")
        for cat, urls in categories.items():
            print(f"   {cat}: {len(urls)} URLs")
            if "accommodation" in cat.lower() or "hotel" in cat.lower() or "accomodation" in cat.lower():
                accommodation_urls = urls
                print(f"   ✅ Found matching category: {cat}")
    
    if not accommodation_urls:
        print("\n❌ No accommodation URLs found in sheet!")
        print("Available categories:")
        for cat in categories.keys():
            print(f"   - {cat}")
        return
    
    print(f"\n📋 URLs to scrape ({len(accommodation_urls)}):")
    for i, url in enumerate(accommodation_urls, 1):
        print(f"   {i}. {url}")
    
    # Scrape each URL
    scraper = ContentScraper()
    all_hotels = []
    
    for i, url in enumerate(accommodation_urls, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(accommodation_urls)}] Scraping: {url[:70]}...")
        print(f"{'='*80}")
        
        try:
            content = await scraper.scrape_url(url, "accommodation_hotels")
            
            if not content:
                print(f"   ❌ Failed to scrape content")
                continue
            
            print(f"   ✅ Scraped {len(content.get('content_text', ''))} chars")
            print(f"   Title: {content.get('title', 'N/A')[:80]}")
            
            # Extract hotel entities using LLM
            print(f"\n   [Extracting hotel entities with LLM...]")
            entities = await entity_extractor.extract_entities(content, "accommodation_hotels")
            
            print(f"   ✅ Extracted {len(entities)} hotel entities")
            
            for j, entity in enumerate(entities, 1):
                name = entity.get("hotel_name") or entity.get("name") or entity.get("title") or "Unknown"
                address = entity.get("address", "N/A")
                print(f"\n      Entity {j}: {name}")
                if address and address != "N/A":
                    print(f"         Address: {address[:80]}")
                if entity.get("amenities"):
                    print(f"         Amenities: {entity.get('amenities')}")
                if entity.get("price_range"):
                    print(f"         Price Range: {entity.get('price_range')}")
            
            all_hotels.extend(entities)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save all hotels to InstantDB
    if all_hotels:
        print(f"\n{'='*80}")
        print(f"[Saving {len(all_hotels)} hotels to InstantDB...]")
        print(f"{'='*80}")
        
        collection_name = instantdb_client._get_collection_for_category("accommodation_hotels")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, hotel in enumerate(all_hotels):
            hotel["category"] = "accommodation_hotels"
            hotel_url = f"{accommodation_urls[0] if accommodation_urls else 'unknown'}#hotel_{i}"
            saved = await instantdb_client.save_scraped_content(hotel_url, hotel)
            if saved:
                saved_count += 1
                name = hotel.get("hotel_name") or hotel.get("name") or "Unknown"
                print(f"   ✅ Saved: {name}")
        
        print(f"\n✅ Successfully saved {saved_count}/{len(all_hotels)} hotels")
    else:
        print("\n⚠️  No hotels extracted from any URLs")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("[Verifying InstantDB...]")
    print(f"{'='*80}")
    await asyncio.sleep(3)
    
    items = await instantdb_client.get_scraped_content_by_category("accommodation_hotels")
    print(f"\n✅ Total hotels in InstantDB: {len(items)}")
    
    if items:
        print("\n📋 Sample hotels:")
        for i, item in enumerate(items[:10], 1):
            name = item.get("hotel_name") or item.get("name") or item.get("title") or "Unknown"
            print(f"\n   {i}. {name}")
            if item.get("address"):
                print(f"      Address: {item.get('address')[:80]}")
            if item.get("amenities"):
                print(f"      Amenities: {item.get('amenities')}")
            if item.get("price_range"):
                print(f"      Price Range: {item.get('price_range')}")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(scrape_accommodation())
