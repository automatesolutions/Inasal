"""Create missing InstantDB collections for accommodation_hotels and restaurants_food"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.instantdb_client import instantdb_client

async def create_missing_collections():
    """Create placeholder entries to ensure collections exist"""
    print("=" * 80)
    print("CREATING MISSING INSTANTDB COLLECTIONS")
    print("=" * 80)
    
    if not instantdb_client._is_available():
        print("❌ InstantDB not available")
        return
    
    missing_categories = ["accommodation_hotels", "restaurants_food"]
    
    for category in missing_categories:
        print(f"\n[Creating collection for {category}...]")
        collection_name = instantdb_client._get_collection_for_category(category)
        await instantdb_client._ensure_collection_exists(collection_name)
        print(f"   ✅ Collection '{collection_name}' ensured")
    
    print("\n" + "=" * 80)
    print("COLLECTIONS CREATED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(create_missing_collections())
