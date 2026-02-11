"""
Test script to check scraping status and test scraping functionality
"""

import asyncio
import httpx
import json
import sys
from typing import Optional

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

BASE_URL = "http://localhost:8000"


async def check_scraped_content():
    """Check what scraped content exists in InstantDB"""
    print("\n" + "=" * 80)
    print("🔍 CHECKING SCRAPED CONTENT STATUS")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/api/admin/check-scraped-content")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data.get('ok', False)}")
                print(f"📊 Message: {data.get('message', 'N/A')}")
                print(f"\n📋 Curated URLs by Category:")
                curated = data.get("curated_urls_by_category", {})
                for category, count in curated.items():
                    print(f"   {category}: {count} URLs")
                
                print(f"\n📋 Scraped Content by Category:")
                scraped = data.get("scraped_content_by_category", {})
                total_scraped = data.get("total_scraped_items", 0)
                
                if total_scraped == 0:
                    print("   ⚠️  NO SCRAPED CONTENT FOUND!")
                    print("   This means scraping has not been executed yet.")
                else:
                    for category, count in scraped.items():
                        print(f"   {category}: {count} items")
                
                print(f"\n📋 Sample Items:")
                samples = data.get("sample_items", {})
                for category, sample in samples.items():
                    print(f"\n   Category: {category}")
                    print(f"      URL: {sample.get('url', 'N/A')}")
                    print(f"      Title: {sample.get('title', 'N/A')}")
                    print(f"      Has Description: {sample.get('has_description', False)}")
                    print(f"      Has Images: {sample.get('has_images', False)}")
                    print(f"      Has Location: {sample.get('has_location', False)}")
                    print(f"      Has Events: {sample.get('has_events', False)}")
                    print(f"      Has Personality Keywords: {sample.get('has_personality_keywords', False)}")
                
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
    except httpx.ConnectError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the backend server is running:")
        print("   cd backend && poetry run uvicorn app.main:app --reload --port 8000")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_scrape_sheet_content(use_instantdb: bool = False):
    """Test scraping content from Google Sheet"""
    print("\n" + "=" * 80)
    print("🚀 TESTING SCRAPING FROM GOOGLE SHEET")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # Long timeout for scraping
            url = f"{BASE_URL}/api/admin/scrape-sheet-content"
            params = {"use_instantdb": use_instantdb}
            
            print(f"📡 Calling: {url}")
            print(f"   Parameters: use_instantdb={use_instantdb}")
            print("   ⏳ This may take several minutes...")
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Scraping completed!")
                print(f"   Status: {data.get('ok', False)}")
                print(f"   Message: {data.get('message', 'N/A')}")
                print(f"   Total URLs Attempted: {data.get('total_urls_attempted', 0)}")
                print(f"   Total URLs Scraped: {data.get('total_urls_scraped', 0)}")
                
                print(f"\n📊 Results by Category:")
                by_category = data.get("scraped_by_category", {})
                for category, count in by_category.items():
                    print(f"   {category}: {count} items")
                
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
    except httpx.ConnectError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the backend server is running")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_batch_scrape(use_existing_urls: bool = False, max_concurrent: int = 3):
    """Test batch scraping with progress tracking"""
    print("\n" + "=" * 80)
    print("🚀 TESTING BATCH SCRAPING")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # Very long timeout
            url = f"{BASE_URL}/api/admin/batch-scrape"
            params = {
                "use_existing_urls": use_existing_urls,
                "max_concurrent": max_concurrent
            }
            
            print(f"📡 Calling: {url}")
            print(f"   Parameters: {params}")
            print("   ⏳ This may take several minutes...")
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Batch scraping completed!")
                print(f"   Status: {data.get('ok', False)}")
                print(f"   Message: {data.get('message', 'N/A')}")
                print(f"   Total URLs: {data.get('total_urls', 0)}")
                print(f"   Total Scraped: {data.get('total_scraped', 0)}")
                
                progress = data.get("progress", {})
                if progress:
                    print(f"\n📊 Progress Details:")
                    print(f"   Completed: {progress.get('completed', 0)}")
                    print(f"   Failed: {progress.get('failed', 0)}")
                    print(f"   Progress: {progress.get('progress_percent', 0)}%")
                    print(f"   Elapsed: {progress.get('elapsed_seconds', 0)}s")
                
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
    except httpx.ConnectError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the backend server is running")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 SCRAPING DIAGNOSTIC TEST")
    print("=" * 80)
    
    # Step 1: Check current status
    status = await check_scraped_content()
    
    if status is None:
        print("\n❌ Cannot connect to backend. Please start the server first.")
        return
    
    total_scraped = status.get("total_scraped_items", 0)
    
    if total_scraped == 0:
        print("\n" + "=" * 80)
        print("⚠️  NO SCRAPED CONTENT FOUND")
        print("=" * 80)
        print("\n🚀 Starting scraping from Google Sheet...")
        print("   (This will take several minutes)")
        
        # Automatically start scraping
        result = await test_scrape_sheet_content(use_instantdb=False)
        if result:
            # Check again after scraping
            print("\n" + "=" * 80)
            print("🔍 CHECKING STATUS AFTER SCRAPING")
            print("=" * 80)
            await check_scraped_content()
    else:
        print("\n✅ Scraped content exists!")
        print(f"   Total items: {total_scraped}")
        print("\nTo re-scrape, you can run:")
        print("   python test_scraping.py --scrape")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    if "--scrape" in sys.argv:
        # Force scraping
        asyncio.run(test_scrape_sheet_content(use_instantdb=False))
    else:
        asyncio.run(main())
