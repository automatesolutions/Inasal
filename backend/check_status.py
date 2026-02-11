"""
Quick script to check scraping status
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def check_status():
    """Check scraped content status"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Checking scraped content status...")
            response = await client.get(f"{BASE_URL}/api/admin/check-scraped-content")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Status: {data.get('ok', False)}")
                print(f"📊 Message: {data.get('message', 'N/A')}")
                print(f"\n📋 Scraped Content by Category:")
                scraped = data.get("scraped_content_by_category", {})
                total = data.get("total_scraped_items", 0)
                
                if total == 0:
                    print("   ⚠️  NO SCRAPED CONTENT FOUND")
                else:
                    for category, count in scraped.items():
                        print(f"   {category}: {count} items")
                    print(f"\n   Total: {total} items")
                
                print(f"\n📋 Sample Items:")
                samples = data.get("sample_items", {})
                if samples:
                    for category, sample in samples.items():
                        print(f"\n   {category}:")
                        print(f"      URL: {sample.get('url', 'N/A')}")
                        print(f"      Title: {sample.get('title', 'N/A')}")
                        print(f"      Has Description: {sample.get('has_description', False)}")
                        print(f"      Has Images: {sample.get('has_images', False)}")
                        print(f"      Has Location: {sample.get('has_location', False)}")
                else:
                    print("   No sample items available")
                
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(check_status())
