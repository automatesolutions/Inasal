"""
Test the complete workflow: Sheet scraping → Category organization → Recommendations
"""

import asyncio
import httpx
import json
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

BASE_URL = "http://localhost:8000"


async def test_complete_workflow():
    """Test the complete workflow"""
    print("=" * 80)
    print("TESTING COMPLETE SHEET SCRAPING WORKFLOW")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        # Step 1: Check current status
        print("\n[Step 1] Checking current category status...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/category-summary")
            if response.status_code == 200:
                data = response.json()
                print(f"   Categories: {data.get('total_categories', 0)}")
                print(f"   Total URLs: {data.get('total_urls', 0)}")
                print(f"   Scraped Items: {data.get('total_scraped_items', 0)}")
                
                categories = data.get("categories", {})
                for slug, info in categories.items():
                    print(f"\n   {slug}:")
                    print(f"      URLs: {info.get('urls_count', 0)}")
                    print(f"      Scraped: {info.get('scraped_items_count', 0)}")
                    print(f"      Last Updated: {info.get('last_updated', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Step 2: Sync and scrape all
        print("\n[Step 2] Syncing Google Sheet and scraping all URLs...")
        print("   (This will take several minutes)")
        try:
            response = await client.get(
                f"{BASE_URL}/api/admin/sync-and-scrape-all",
                params={"force_rescrape": False, "max_concurrent": 5}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"\n   Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
                print(f"   Message: {data.get('message', 'N/A')}")
                
                if data.get("scraping_performed"):
                    results = data.get("scraping_results", {})
                    print(f"\n   Scraping Results:")
                    print(f"      Attempted: {results.get('total_urls_attempted', 0)}")
                    print(f"      Scraped: {results.get('total_urls_scraped', 0)}")
                    print(f"      Success Rate: {results.get('success_rate', 0)}%")
                    
                    by_category = results.get("by_category", {})
                    if by_category:
                        print(f"\n   By Category:")
                        for cat, count in by_category.items():
                            print(f"      {cat}: {count} items")
                else:
                    print(f"   No scraping performed (no new links detected)")
                
                print(f"\n   Categories:")
                print(f"      New: {data.get('new_categories', [])}")
                print(f"      Updated: {data.get('updated_categories', [])}")
                print(f"      Unchanged: {len(data.get('unchanged_categories', []))}")
            else:
                print(f"   Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Step 3: Verify scraped content
        print("\n[Step 3] Verifying scraped content by category...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/check-scraped-content")
            if response.status_code == 200:
                data = response.json()
                scraped = data.get("scraped_content_by_category", {})
                total = data.get("total_scraped_items", 0)
                
                if total > 0:
                    print(f"   Total scraped items: {total}")
                    print(f"\n   By Category:")
                    for cat, count in scraped.items():
                        print(f"      {cat}: {count} items")
                    
                    samples = data.get("sample_items", {})
                    if samples:
                        print(f"\n   Sample Items:")
                        for cat, sample in list(samples.items())[:3]:  # Show first 3
                            print(f"\n      {cat}:")
                            print(f"         URL: {sample.get('url', 'N/A')[:60]}...")
                            print(f"         Title: {sample.get('title', 'N/A')[:60]}...")
                            print(f"         Has Description: {sample.get('has_description', False)}")
                            print(f"         Has Images: {sample.get('has_images', False)}")
                            print(f"         Has Location: {sample.get('has_location', False)}")
                else:
                    print("   No scraped content found")
            else:
                print(f"   Error: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Step 4: Check category summary again
        print("\n[Step 4] Final category summary...")
        try:
            response = await client.get(f"{BASE_URL}/api/admin/category-summary")
            if response.status_code == 200:
                data = response.json()
                print(f"   Total Categories: {data.get('total_categories', 0)}")
                print(f"   Total URLs: {data.get('total_urls', 0)}")
                print(f"   Total Scraped Items: {data.get('total_scraped_items', 0)}")
                
                categories = data.get("categories", {})
                print(f"\n   Category Details:")
                for slug, info in categories.items():
                    urls = info.get("urls_count", 0)
                    scraped = info.get("scraped_items_count", 0)
                    coverage = round((scraped / urls * 100) if urls > 0 else 0, 1)
                    print(f"      {slug}: {scraped}/{urls} scraped ({coverage}%)")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Generate recommendations for a user")
    print("2. Check backend logs for 'Enhancing item with scraped content'")
    print("3. Verify recommendations show images and rich descriptions")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
