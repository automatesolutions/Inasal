"""Debug: Check what restaurants are actually mentioned in the content"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.content_scraper import ContentScraper

async def debug():
    url = "https://thepinaysolobackpacker.com/bacolod-things-to-do"
    scraper = ContentScraper()
    
    print("Scraping URL...")
    content = await scraper.scrape_url(url, "restaurants_food")
    
    if content:
        print(f"\nTitle: {content.get('title')}")
        print(f"\nDescription: {content.get('description')[:200]}...")
        print(f"\nContent Text Length: {len(content.get('content_text', ''))} chars")
        print(f"\nFirst 2000 chars of content:")
        print("=" * 80)
        print(content.get('content_text', '')[:2000])
        print("=" * 80)
        
        # Search for restaurant keywords
        text = content.get('content_text', '').lower()
        restaurant_keywords = ['restaurant', 'cafe', 'eatery', 'food', 'dining', 'manokan', 'calea', 'bob', 'chicken inasal']
        print(f"\nSearching for restaurant mentions...")
        for keyword in restaurant_keywords:
            count = text.count(keyword)
            if count > 0:
                print(f"  '{keyword}': found {count} times")

if __name__ == "__main__":
    asyncio.run(debug())
