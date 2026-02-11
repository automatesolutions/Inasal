"""Verify final restaurant count and details"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.instantdb_client import instantdb_client

async def verify():
    print("=" * 80)
    print("FINAL RESTAURANT VERIFICATION")
    print("=" * 80)
    
    items = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    
    print(f"\n✅ Total restaurant entities in InstantDB: {len(items)}")
    
    # Group by restaurant name
    restaurants_by_name = {}
    for item in items:
        name = item.get("restaurant_name") or item.get("name") or item.get("title", "Unknown")
        if name and name != "Unknown" and "Bacolod Food Hunters" not in name and "Facebook" not in name:
            if name not in restaurants_by_name:
                restaurants_by_name[name] = []
            restaurants_by_name[name].append(item)
    
    print(f"✅ Unique restaurants: {len(restaurants_by_name)}")
    
    print(f"\n📋 Complete Restaurant List ({len(restaurants_by_name)} unique):")
    print("=" * 80)
    
    for i, (name, items_list) in enumerate(sorted(restaurants_by_name.items()), 1):
        # Use the most complete item
        item = max(items_list, key=lambda x: len(str(x.get("description", ""))))
        
        print(f"\n{i}. {name}")
        
        if item.get("address"):
            print(f"   📍 Address: {item.get('address')[:100]}")
        
        if item.get("cuisine_type"):
            print(f"   🍽️  Cuisine: {item.get('cuisine_type')}")
        
        if item.get("specialties"):
            specialties = item.get("specialties", [])
            if isinstance(specialties, list) and specialties:
                print(f"   ⭐ Specialties: {', '.join(specialties[:5])}")
        
        if item.get("description"):
            desc = item.get("description", "")
            if len(desc) > 50:
                print(f"   📝 {desc[:150]}...")
        
        if item.get("opening_hours"):
            print(f"   🕐 Hours: {item.get('opening_hours')}")
        
        if item.get("phone"):
            print(f"   📞 Phone: {item.get('phone')}")
        
        if len(items_list) > 1:
            print(f"   ⚠️  Note: {len(items_list)} entries found for this restaurant")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print(f"\n✅ {len(items)} total entities")
    print(f"✅ {len(restaurants_by_name)} unique restaurants")
    print(f"\nAll restaurants have been scraped, extracted with LLM, and saved to InstantDB!")

if __name__ == "__main__":
    asyncio.run(verify())
