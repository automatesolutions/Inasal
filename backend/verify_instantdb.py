"""Verify InstantDB data storage"""

import asyncio
import httpx
import json
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

BASE_URL = "http://localhost:8000"

async def verify():
    print("=" * 80)
    print("VERIFYING INSTANTDB DATA STORAGE")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First, run sync and scrape
        print("\n[Step 1] Running sync-and-scrape-all...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/admin/sync-and-scrape-all",
                params={"force_rescrape": True, "max_concurrent": 3}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
                print(f"   Message: {data.get('message', 'N/A')}")
                if data.get("scraping_results"):
                    results = data["scraping_results"]
                    print(f"   Scraped: {results.get('total_urls_scraped', 0)}/{results.get('total_urls_attempted', 0)} URLs")
            else:
                print(f"   Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Wait for InstantDB propagation
        print("\n[Step 2] Waiting for InstantDB propagation...")
        await asyncio.sleep(5)
        
        # Verify data directly
        print("\n[Step 3] Verifying data in InstantDB...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/verify-instantdb-data")
            if response.status_code == 200:
                data = response.json()
                print(f"\n   Status: {'SUCCESS' if data.get('ok') else 'FAILED'}")
                print(f"   Total Items in DB: {data.get('total_items_in_db', 0)}")
                print(f"   Categories Found: {len(data.get('categories_found', []))}")
                
                items_by_category = data.get("items_by_category", {})
                if items_by_category:
                    print(f"\n   Items by Category:")
                    for cat, count in items_by_category.items():
                        print(f"      {cat}: {count} items")
                else:
                    print("   No items found by category")
                
                sample_items = data.get("sample_items", {})
                if sample_items:
                    print(f"\n   Sample Items:")
                    for cat, sample in list(sample_items.items())[:3]:
                        print(f"\n      Category: {cat}")
                        print(f"         ID: {sample.get('id', 'N/A')}")
                        print(f"         URL: {sample.get('url', 'N/A')}")
                        print(f"         Title: {sample.get('title', 'N/A')}")
                        print(f"         Has Description: {sample.get('has_description', False)}")
                        print(f"         Has Images: {sample.get('has_images', False)}")
                        print(f"         Has Location: {sample.get('has_location', False)}")
                        print(f"         Has Events: {sample.get('has_events', False)}")
                        print(f"         Has Personality Keywords: {sample.get('has_personality_keywords', False)}")
                        print(f"         Scraped At: {sample.get('scraped_at', 'N/A')}")
                else:
                    print("   No sample items available")
                
                print(f"\n   Message: {data.get('message', 'N/A')}")
            else:
                print(f"   Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Check category summary
        print("\n[Step 4] Checking category summary...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/category-summary")
            if response.status_code == 200:
                data = response.json()
                print(f"   Total Categories: {data.get('total_categories', 0)}")
                print(f"   Total URLs: {data.get('total_urls', 0)}")
                print(f"   Total Scraped Items: {data.get('total_scraped_items', 0)}")
                
                categories = data.get("categories", {})
                if categories:
                    print(f"\n   Category Details:")
                    for slug, info in categories.items():
                        urls = info.get("urls_count", 0)
                        scraped = info.get("scraped_items_count", 0)
                        coverage = round((scraped / urls * 100) if urls > 0 else 0, 1)
                        print(f"      {slug}:")
                        print(f"         URLs: {urls}")
                        print(f"         Scraped Items: {scraped}")
                        print(f"         Coverage: {coverage}%")
                        print(f"         Last Updated: {info.get('last_updated', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify())
