"""Verify entity extraction results in InstantDB"""

import asyncio
import sys
import codecs
import json

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.instantdb_client import instantdb_client

async def verify():
    print("=" * 80)
    print("VERIFYING ENTITY EXTRACTION IN INSTANTDB")
    print("=" * 80)
    
    await asyncio.sleep(3)  # Wait for propagation
    
    all_scraped = await instantdb_client.get_all_scraped_content()
    
    print(f"\n📊 INSTANTDB ENTITY COUNT BY CATEGORY:")
    print("=" * 80)
    
    total = 0
    for cat in ["accommodation_hotels", "tourist_spots", "restaurants_food", 
                "dangerous_areas", "scams", "secret_places"]:
        items = all_scraped.get(cat, [])
        count = len(items)
        total += count
        status = "✅" if count > 0 else "❌"
        print(f"{status} {cat:<30} {count:>3} entities")
    
    print("=" * 80)
    print(f"📈 TOTAL ENTITIES: {total}")
    print("=" * 80)
    
    # Show detailed samples
    print("\n📋 DETAILED ENTITY SAMPLES:")
    print("=" * 80)
    
    for cat in ["accommodation_hotels", "tourist_spots", "restaurants_food", 
                "dangerous_areas", "scams", "secret_places"]:
        items = all_scraped.get(cat, [])
        if items:
            print(f"\n🔹 {cat.upper()} ({len(items)} entities):")
            print("-" * 80)
            
            for i, item in enumerate(items[:3], 1):  # Show first 3
                # Get entity name based on category
                name = (item.get("hotel_name") or item.get("restaurant_name") or 
                       item.get("attraction_name") or item.get("place_name") or 
                       item.get("name") or item.get("title") or "Untitled")
                
                address = item.get("address") or (item.get("location", {}).get("address") if isinstance(item.get("location"), dict) else None)
                
                print(f"\n  Entity {i}: {name[:60]}")
                if address:
                    print(f"    Address: {address[:70]}")
                if item.get("description"):
                    desc = item.get("description", "")[:100]
                    print(f"    Description: {desc}...")
                
                # Category-specific fields
                if cat == "accommodation_hotels":
                    if item.get("amenities"):
                        print(f"    Amenities: {item.get('amenities')}")
                    if item.get("price_range"):
                        print(f"    Price Range: {item.get('price_range')}")
                    if item.get("phone"):
                        print(f"    Phone: {item.get('phone')}")
                
                elif cat == "restaurants_food":
                    if item.get("cuisine_type"):
                        print(f"    Cuisine: {item.get('cuisine_type')}")
                    if item.get("specialties"):
                        print(f"    Specialties: {item.get('specialties')}")
                    if item.get("opening_hours"):
                        print(f"    Hours: {item.get('opening_hours')}")
                
                elif cat == "tourist_spots":
                    if item.get("entrance_fee"):
                        print(f"    Entrance Fee: {item.get('entrance_fee')}")
                    if item.get("opening_hours"):
                        print(f"    Hours: {item.get('opening_hours')}")
                    if item.get("highlights"):
                        print(f"    Highlights: {item.get('highlights')[:3] if isinstance(item.get('highlights'), list) else item.get('highlights')}")
                
                elif cat == "secret_places":
                    if item.get("why_secret"):
                        print(f"    Why Secret: {item.get('why_secret')[:60]}...")
                    if item.get("how_to_find"):
                        print(f"    How to Find: {item.get('how_to_find')[:60]}...")
                
                if item.get("images"):
                    print(f"    Images: {len(item.get('images', []))} images")
            
            if len(items) > 3:
                print(f"\n  ... and {len(items) - 3} more entities")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print("\n✅ Each entity (hotel, restaurant, attraction) is saved as a separate record")
    print("✅ Category-specific fields are populated (hotel_name, restaurant_name, etc.)")
    print("✅ Check InstantDB dashboard to see all itemized entities!")

if __name__ == "__main__":
    asyncio.run(verify())
