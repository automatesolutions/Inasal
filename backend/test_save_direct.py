"""Test direct save to InstantDB to verify it works"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.instantdb_client import instantdb_client

async def test_direct_save():
    """Test saving a sample item directly to InstantDB"""
    print("=" * 80)
    print("TESTING DIRECT SAVE TO INSTANTDB")
    print("=" * 80)
    
    if not instantdb_client._is_available():
        print("❌ InstantDB not available")
        return
    
    # Create a test item
    test_content = {
        "url": "https://example.com/test",
        "category": "tourist_spots",
        "title": "Test Attraction",
        "description": "This is a test description",
        "content_text": "Full content text here",
        "images": ["https://example.com/image.jpg"],
        "places_mentioned": ["Bacolod City"],
        "domain": "example.com",
        "location": {
            "address": "123 Test St, Bacolod City",
            "latitude": 10.6407,
            "longitude": 122.9689,
            "city": "Bacolod City",
            "region": "Negros Occidental"
        },
        "events": [],
        "personality_keywords": {
            "adventurous": 0.5,
            "cultural": 0.7
        }
    }
    
    print(f"\n[Step 1] Saving test item to InstantDB...")
    print(f"   URL: {test_content['url']}")
    print(f"   Category: {test_content['category']}")
    
    saved = await instantdb_client.save_scraped_content(test_content['url'], test_content)
    
    if saved:
        print("   ✅ Save reported success")
    else:
        print("   ❌ Save reported failure")
        return
    
    # Wait for propagation
    print("\n[Step 2] Waiting for InstantDB propagation...")
    await asyncio.sleep(3)
    
    # Try to retrieve it
    print("\n[Step 3] Retrieving test item from InstantDB...")
    items = await instantdb_client.get_scraped_content_by_category("tourist_spots")
    
    print(f"   Found {len(items)} items for category 'tourist_spots'")
    
    # Check if our test item is there
    test_found = False
    for item in items:
        if item.get("url") == test_content['url']:
            test_found = True
            print(f"\n   ✅ Test item found!")
            print(f"      ID: {item.get('id')}")
            print(f"      Title: {item.get('title')}")
            print(f"      Category: {item.get('category')}")
            print(f"      Has Location: {bool(item.get('location'))}")
            break
    
    if not test_found:
        print("   ❌ Test item NOT found in InstantDB")
        print("   This suggests the save operation may not be working correctly")
    
    # Also try getting all scraped content
    print("\n[Step 4] Getting all scraped content...")
    all_scraped = await instantdb_client.get_all_scraped_content()
    total = sum(len(items) for items in all_scraped.values())
    print(f"   Total items: {total}")
    print(f"   Categories: {list(all_scraped.keys())}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_direct_save())
