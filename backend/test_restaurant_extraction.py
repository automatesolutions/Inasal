"""Test restaurant entity extraction specifically"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from app.sheets_sync import fetch_and_parse_sheet
from app.content_scraper import ContentScraper
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def test_restaurant_extraction():
    print("=" * 80)
    print("TESTING RESTAURANT ENTITY EXTRACTION")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    
    print("\n[Step 1] Checking URLs in Google Sheet:")
    for cat, urls in categories.items():
        print(f"   {cat}: {len(urls)} URLs")
        for url in urls:
            print(f"      - {url}")
    
    # Check restaurants_food URLs
    restaurant_urls = categories.get("restaurants_food", [])
    print(f"\n[Step 2] Restaurant URLs found: {len(restaurant_urls)}")
    
    if not restaurant_urls:
        print("   ❌ No restaurant URLs in Google Sheet!")
        return
    
    # Scrape first restaurant URL
    scraper = ContentScraper()
    test_url = restaurant_urls[0]
    
    print(f"\n[Step 3] Scraping restaurant URL: {test_url}")
    content = await scraper.scrape_url(test_url, "restaurants_food")
    
    if not content:
        print("   ❌ Failed to scrape content")
        return
    
    print(f"   ✅ Scraped content:")
    print(f"      Title: {content.get('title', 'N/A')[:80]}")
    print(f"      Description: {content.get('description', 'N/A')[:100]}...")
    print(f"      Content length: {len(content.get('content_text', ''))} chars")
    
    # Extract entities
    print(f"\n[Step 4] Extracting restaurant entities using LLM...")
    entities = await entity_extractor.extract_entities(content, "restaurants_food")
    
    print(f"   ✅ Extracted {len(entities)} restaurant entities")
    
    for i, entity in enumerate(entities, 1):
        print(f"\n   Entity {i}:")
        print(f"      restaurant_name: {entity.get('restaurant_name', 'N/A')}")
        print(f"      address: {entity.get('address', 'N/A')}")
        print(f"      cuisine_type: {entity.get('cuisine_type', 'N/A')}")
        print(f"      specialties: {entity.get('specialties', [])}")
        print(f"      opening_hours: {entity.get('opening_hours', 'N/A')}")
        print(f"      phone: {entity.get('phone', 'N/A')}")
        print(f"      images: {len(entity.get('images', []))} images")
    
    # Save to InstantDB
    print(f"\n[Step 5] Saving entities to InstantDB...")
    collection_name = instantdb_client._get_collection_for_category("restaurants_food")
    await instantdb_client._ensure_collection_exists(collection_name)
    
    saved_count = 0
    for i, entity in enumerate(entities):
        entity_url = f"{test_url}#entity_{i}" if len(entities) > 1 else test_url
        saved = await instantdb_client.save_scraped_content(entity_url, entity)
        if saved:
            saved_count += 1
    
    print(f"   ✅ Saved {saved_count}/{len(entities)} entities")
    
    # Verify in InstantDB
    print(f"\n[Step 6] Verifying in InstantDB...")
    await asyncio.sleep(3)
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    print(f"   ✅ Found {len(items)} restaurant entities in InstantDB")
    
    for i, item in enumerate(items[:5], 1):
        print(f"\n   Item {i}:")
        print(f"      ID: {item.get('id')}")
        print(f"      restaurant_name: {item.get('restaurant_name', 'N/A')}")
        print(f"      name: {item.get('name', 'N/A')}")
        print(f"      title: {item.get('title', 'N/A')}")
        print(f"      address: {item.get('address', 'N/A')}")
        print(f"      cuisine_type: {item.get('cuisine_type', 'N/A')}")
        print(f"      specialties: {item.get('specialties', [])}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_restaurant_extraction())
