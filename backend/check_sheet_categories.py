"""Check what categories and URLs are actually in the Google Sheet"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_and_parse_sheet

async def check():
    print("=" * 80)
    print("CHECKING GOOGLE SHEET CATEGORIES AND URLS")
    print("=" * 80)
    
    categories = await fetch_and_parse_sheet()
    
    print(f"\nCategories found: {len(categories)}")
    print("\n" + "=" * 80)
    
    for cat, urls in sorted(categories.items()):
        print(f"\n📁 {cat.upper()}: {len(urls)} URLs")
        if urls:
            for i, url in enumerate(urls, 1):
                print(f"   {i}. {url}")
        else:
            print("   ⚠️  NO URLs FOUND IN THIS CATEGORY")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total = sum(len(urls) for urls in categories.values())
    print(f"Total URLs: {total}")
    
    # Check specifically for accommodation_hotels
    if "accommodation_hotels" in categories:
        hotel_urls = categories["accommodation_hotels"]
        print(f"\n⚠️  accommodation_hotels: {len(hotel_urls)} URLs")
        if len(hotel_urls) == 0:
            print("   ❌ NO URLs in Google Sheet for accommodation_hotels!")
            print("   This is why there's no data - you need to add hotel URLs to the sheet.")
    
    # Check restaurants_food
    if "restaurants_food" in categories:
        restaurant_urls = categories["restaurants_food"]
        print(f"\n⚠️  restaurants_food: {len(restaurant_urls)} URLs")
        print(f"   URLs: {restaurant_urls}")
        if len(restaurant_urls) == 1:
            print("   ⚠️  Only 1 URL (the other is Facebook which fails to scrape)")

if __name__ == "__main__":
    asyncio.run(check())
