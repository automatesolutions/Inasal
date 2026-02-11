"""Verify accommodation hotels in InstantDB"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.instantdb_client import instantdb_client

async def verify():
    print("=" * 80)
    print("VERIFYING ACCOMMODATION HOTELS IN INSTANTDB")
    print("=" * 80)
    
    items = await instantdb_client.get_scraped_content_by_category("accommodation_hotels")
    print(f"\n✅ Total hotels in InstantDB: {len(items)}\n")
    
    # Filter for actual hotels (not tourist spots that got mixed in)
    hotels = []
    for item in items:
        name = item.get("hotel_name") or item.get("name") or item.get("title", "")
        if name and ("hotel" in name.lower() or "resort" in name.lower() or "inn" in name.lower() or "condo" in name.lower() or "accommodation" in name.lower() or "palmas" in name.lower() or "l'fisher" in name.lower() or "seda" in name.lower()):
            hotels.append(item)
    
    print(f"📋 Found {len(hotels)} actual hotel/accommodation entities:\n")
    
    for i, item in enumerate(hotels[:20], 1):
        name = item.get("hotel_name") or item.get("name") or item.get("title", "Unknown")
        print(f"{i}. {name}")
        if item.get("address"):
            print(f"   Address: {item.get('address')[:80]}")
        if item.get("amenities"):
            print(f"   Amenities: {item.get('amenities')}")
        if item.get("price_range"):
            print(f"   Price Range: {item.get('price_range')}")
        print()

if __name__ == "__main__":
    asyncio.run(verify())
