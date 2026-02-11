"""Full scrape of all URLs from Google Sheet and organize by category"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

import httpx
from app.services.sheet_scraping_service import SheetScrapingService
from app.instantdb_client import instantdb_client

BASE_URL = "http://localhost:8000"

async def full_scrape():
    print("=" * 80)
    print("FULL SCRAPE OF ALL URLs FROM GOOGLE SHEET")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("\n[Step 1] Running comprehensive sync-and-scrape-all...")
        print("   This will scrape ALL URLs from ALL categories")
        print("   This may take 10-20 minutes depending on the number of URLs...")
        
        try:
            response = await client.get(
                f"{BASE_URL}/api/admin/sync-and-scrape-all",
                params={
                    "force_rescrape": True,  # Force scraping even if no new links
                    "max_concurrent": 3  # Lower concurrency to avoid overwhelming servers
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n   ✅ Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
                print(f"   Message: {data.get('message', 'N/A')}")
                
                if data.get("scraping_results"):
                    results = data["scraping_results"]
                    print(f"\n   Scraping Results:")
                    print(f"      Total URLs Attempted: {results.get('total_urls_attempted', 0)}")
                    print(f"      Total URLs Scraped: {results.get('total_urls_scraped', 0)}")
                    print(f"      Success Rate: {results.get('success_rate', 0)}%")
                    
                    by_category = results.get("by_category", {})
                    if by_category:
                        print(f"\n   Items Scraped by Category:")
                        for cat, count in by_category.items():
                            print(f"      {cat}: {count} items")
                
                print(f"\n   Categories:")
                print(f"      New: {data.get('new_categories', [])}")
                print(f"      Updated: {data.get('updated_categories', [])}")
                print(f"      Unchanged: {data.get('unchanged_categories', [])}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Wait for InstantDB propagation
        print("\n[Step 2] Waiting for InstantDB propagation...")
        await asyncio.sleep(5)
        
        # Verify all categories have data
        print("\n[Step 3] Verifying data in InstantDB by category...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/verify-instantdb-data")
            if response.status_code == 200:
                data = response.json()
                print(f"\n   ✅ Verification Status: {'SUCCESS' if data.get('ok') else 'FAILED'}")
                print(f"   Total Items in DB: {data.get('total_items_in_db', 0)}")
                print(f"   Categories Found: {len(data.get('categories_found', []))}")
                
                items_by_category = data.get("items_by_category", {})
                if items_by_category:
                    print(f"\n   Items by Category:")
                    total = 0
                    for cat, count in sorted(items_by_category.items()):
                        print(f"      {cat}: {count} items")
                        total += count
                    print(f"\n   Total: {total} items across {len(items_by_category)} categories")
                else:
                    print("   ⚠️  No items found by category")
                
                # Check each expected category
                expected_categories = [
                    "accommodation_hotels",
                    "tourist_spots",
                    "restaurants_food",
                    "dangerous_areas",
                    "scams",
                    "secret_places"
                ]
                
                print(f"\n   Expected Categories Status:")
                for cat in expected_categories:
                    count = items_by_category.get(cat, 0)
                    status = "✅" if count > 0 else "❌"
                    print(f"      {status} {cat}: {count} items")
            else:
                print(f"   ❌ Verification failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error verifying: {e}")
        
        # Get category summary
        print("\n[Step 4] Getting category summary...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/category-summary")
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"\n   Total Categories: {data.get('total_categories', 0)}")
                    print(f"   Total URLs: {data.get('total_urls', 0)}")
                    print(f"   Total Scraped Items: {data.get('total_scraped_items', 0)}")
                    
                    categories = data.get("categories", {})
                    if categories:
                        print(f"\n   Category Details:")
                        for slug, info in sorted(categories.items()):
                            urls = info.get("urls_count", 0)
                            scraped = info.get("scraped_items_count", 0)
                            coverage = round((scraped / urls * 100) if urls > 0 else 0, 1)
                            print(f"\n      {slug}:")
                            print(f"         URLs: {urls}")
                            print(f"         Scraped Items: {scraped}")
                            print(f"         Coverage: {coverage}%")
                            print(f"         Last Updated: {info.get('last_updated', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error getting summary: {e}")
    
    print("\n" + "=" * 80)
    print("FULL SCRAPE COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Check InstantDB dashboard to see the data organized by category")
    print("2. Verify recommendations are using scraped content")
    print("3. Test recommendation generation for a user")

if __name__ == "__main__":
    asyncio.run(full_scrape())
