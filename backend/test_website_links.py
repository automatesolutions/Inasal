"""Test website link extraction from Facebook"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.content_scraper import ContentScraper

async def test():
    scraper = ContentScraper()
    url = "https://www.facebook.com/BacolodFoodHunters/"
    
    print("Scraping Facebook page...")
    content = await scraper.scrape_url(url, "restaurants_food")
    
    if content:
        website_links = content.get("website_links", [])
        print(f"\nWebsite links found: {len(website_links)}")
        for link in website_links:
            print(f"  - {link}")
    else:
        print("No content")

if __name__ == "__main__":
    asyncio.run(test())
