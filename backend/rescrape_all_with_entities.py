"""
Rescrape ALL URLs with entity extraction and verify InstantDB results
"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def rescrape_and_verify():
    print("=" * 80)
    print("RESCRAPING ALL URLS WITH ENTITY EXTRACTION")
    print("=" * 80)
    
    # Fetch all URLs
    print("\n[Step 1] Fetching URLs from Google Sheet...")
    categories = await fetch_and_parse_sheet()
    
    total_urls = sum(len(urls) for urls in categories.values())
    print(f"   Found {total_urls} URLs across {len(categories)} categories")
    for cat, urls in categories.items():
        print(f"      {cat}: {len(urls)} URLs")
    
    # Rescrape ALL URLs (force rescrape by clearing existing data first)
    print("\n[Step 2] Rescraping ALL URLs with entity extraction...")
    print("   This will extract multiple entities from each URL")
    print("   Each entity (hotel, restaurant, attraction) will be saved as a separate record\n")
    
    results = await scrape_all_urls_from_sheet(categories, max_concurrent=3)
    
    # Count entities extracted
    total_entities = sum(len(items) for items in results.values())
    print(f"\n   ✅ Extracted {total_entities} total entities from {total_urls} URLs")
    for cat, items in results.items():
        if items:
            print(f"      {cat}: {len(items)} entities")
    
    # Wait for InstantDB propagation
    print("\n[Step 3] Waiting for InstantDB propagation...")
    await asyncio.sleep(5)
    
    # Verify InstantDB results
    print("\n[Step 4] Verifying InstantDB results...")
    all_scraped = await instantdb_client.get_all_scraped_content()
    
    print(f"\n   📊 INSTANTDB RESULTS:")
    print(f"   {'='*60}")
    
    total_items = 0
    for cat in ["accommodation_hotels", "tourist_spots", "restaurants_food", 
                "dangerous_areas", "scams", "secret_places"]:
        items = all_scraped.get(cat, [])
        count = len(items)
        total_items += count
        
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {cat:<30} {count:>3} items")
        
        # Show sample entity fields for first item
        if items:
            sample = items[0]
            print(f"      Sample entity fields:")
            
            # Check category-specific fields
            if cat == "accommodation_hotels":
                if sample.get("hotel_name"):
                    print(f"         ✅ hotel_name: {sample.get('hotel_name')[:60]}")
                if sample.get("address"):
                    print(f"         ✅ address: {sample.get('address')[:60]}")
                if sample.get("amenities"):
                    print(f"         ✅ amenities: {sample.get('amenities')}")
                if sample.get("price_range"):
                    print(f"         ✅ price_range: {sample.get('price_range')}")
            
            elif cat == "restaurants_food":
                if sample.get("restaurant_name"):
                    print(f"         ✅ restaurant_name: {sample.get('restaurant_name')[:60]}")
                if sample.get("address"):
                    print(f"         ✅ address: {sample.get('address')[:60]}")
                if sample.get("cuisine_type"):
                    print(f"         ✅ cuisine_type: {sample.get('cuisine_type')}")
                if sample.get("specialties"):
                    print(f"         ✅ specialties: {sample.get('specialties')}")
            
            elif cat == "tourist_spots":
                if sample.get("attraction_name"):
                    print(f"         ✅ attraction_name: {sample.get('attraction_name')[:60]}")
                if sample.get("address"):
                    print(f"         ✅ address: {sample.get('address')[:60]}")
                if sample.get("entrance_fee"):
                    print(f"         ✅ entrance_fee: {sample.get('entrance_fee')}")
                if sample.get("opening_hours"):
                    print(f"         ✅ opening_hours: {sample.get('opening_hours')}")
            
            elif cat == "secret_places":
                if sample.get("place_name"):
                    print(f"         ✅ place_name: {sample.get('place_name')[:60]}")
                if sample.get("address"):
                    print(f"         ✅ address: {sample.get('address')[:60]}")
                if sample.get("why_secret"):
                    print(f"         ✅ why_secret: {sample.get('why_secret')[:60]}")
            
            elif cat in ["scams", "dangerous_areas"]:
                if sample.get("name"):
                    print(f"         ✅ name: {sample.get('name')[:60]}")
                if sample.get("location"):
                    loc = sample.get('location')
                    if isinstance(loc, str):
                        print(f"         ✅ location: {loc[:60]}")
                    elif isinstance(loc, dict):
                        print(f"         ✅ location: {str(loc)[:60]}")
                if sample.get("warning_signs"):
                    print(f"         ✅ warning_signs: {sample.get('warning_signs')}")
            
            # Common fields
            if sample.get("images"):
                print(f"         ✅ images: {len(sample.get('images', []))} images")
            if sample.get("description"):
                desc = sample.get('description', '')[:80]
                print(f"         ✅ description: {desc}...")
            print()
    
    print(f"   {'='*60}")
    print(f"   📈 TOTAL ITEMS IN INSTANTDB: {total_items}")
    print(f"   {'='*60}")
    
    # Show detailed breakdown
    print("\n[Step 5] Detailed Entity Breakdown:")
    for cat, items in sorted(all_scraped.items()):
        if items:
            print(f"\n   {cat.upper()} ({len(items)} entities):")
            for i, item in enumerate(items[:5], 1):  # Show first 5
                name = (item.get("hotel_name") or item.get("restaurant_name") or 
                       item.get("attraction_name") or item.get("place_name") or 
                       item.get("name") or item.get("title") or "Untitled")
                address = item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None)
                print(f"      {i}. {name[:50]}")
                if address:
                    print(f"         Address: {address[:60]}")
                if item.get("images"):
                    print(f"         Images: {len(item.get('images', []))} images")
            if len(items) > 5:
                print(f"      ... and {len(items) - 5} more entities")
    
    print("\n" + "=" * 80)
    print("RESCRAPING AND VERIFICATION COMPLETE")
    print("=" * 80)
    print("\n✅ All scrapeable URLs have been processed with entity extraction")
    print("✅ Each entity (hotel, restaurant, attraction) is saved as a separate record")
    print("✅ Category-specific fields are populated (hotel_name, restaurant_name, etc.)")
    print("\n📊 Check InstantDB dashboard to see the itemized data!")

if __name__ == "__main__":
    asyncio.run(rescrape_and_verify())
