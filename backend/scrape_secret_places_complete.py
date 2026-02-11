"""Scrape ALL Secret Places URLs including Facebook URLs from image"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

# Facebook URLs from the user's image
FACEBOOK_SECRET_PLACES_URLS = [
    "https://www.facebook.com/maueeeshappyfeet/videos/no-entrance-sa-hidden-cafe-dito-sa-bacolod-city-maueeeshappyfeet/899770145339469/",
    "https://www.facebook.com/ELGonsSecretGarden/",
    "https://www.facebook.com/BacolodFoodHunters/posts/bacolod-has-lots-of-cool-secret-places-and-one-of-them-is-commis-co-its-right-ne/1194224915395099/"
]

async def scrape_secret_places_complete():
    print("=" * 80)
    print("SCRAPING ALL SECRET PLACES IN BACOLOD")
    print("=" * 80)
    print("\nThis will:")
    print("1. Scrape URLs from Google Sheet")
    print("2. Scrape Facebook URLs for secret places")
    print("3. Use LLM to extract ALL secret places mentioned")
    print("4. Save each secret place as a separate entity to InstantDB")
    print("=" * 80)
    
    # Combine sheet URLs with Facebook URLs
    from app.sheets_sync import fetch_and_parse_sheet
    categories = await fetch_and_parse_sheet()
    sheet_urls = categories.get("secret_places", [])
    
    all_urls = list(set(sheet_urls + FACEBOOK_SECRET_PLACES_URLS))
    
    print(f"\n📋 Total Secret Places URLs to scrape: {len(all_urls)}")
    print(f"   - From Google Sheet: {len(sheet_urls)}")
    print(f"   - Facebook URLs: {len(FACEBOOK_SECRET_PLACES_URLS)}")
    print("\nURLs:")
    for i, url in enumerate(all_urls, 1):
        print(f"   {i}. {url[:100]}...")
    
    # Scrape all URLs
    print(f"\n{'='*80}")
    print("SCRAPING ALL SECRET PLACES URLS...")
    print(f"{'='*80}\n")
    
    results = await scrape_all_urls_from_sheet(
        {"secret_places": all_urls},
        max_concurrent=3
    )
    
    secret_places_results = results.get("secret_places", [])
    print(f"\n✅ Scraped {len(secret_places_results)} URLs successfully")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("VERIFYING INSTANTDB...")
    print(f"{'='*80}")
    await asyncio.sleep(5)  # Wait for propagation
    
    items = await instantdb_client.get_scraped_content_by_category("secret_places")
    print(f"\n✅ Total secret places in InstantDB: {len(items)}")
    
    # Show unique secret places
    unique_places = {}
    for item in items:
        name = item.get("place_name") or item.get("name") or item.get("title", "Unknown")
        if name and name != "Unknown":
            if name not in unique_places:
                unique_places[name] = item
    
    print(f"\n📊 Unique secret places found: {len(unique_places)}")
    print("\n📋 Secret Places List:")
    for i, (name, item) in enumerate(sorted(unique_places.items())[:50], 1):
        print(f"\n   {i}. {name}")
        if item.get("address"):
            print(f"      📍 {item.get('address')[:80]}")
        if item.get("description"):
            desc = item.get("description", "")[:150]
            if desc:
                print(f"      📝 {desc}...")
        if item.get("why_secret"):
            print(f"      🔒 Why Secret: {item.get('why_secret')[:100]}...")
        if item.get("how_to_find"):
            print(f"      🗺️  How to Find: {item.get('how_to_find')[:100]}...")
        if item.get("tips"):
            tips = item.get("tips", [])
            if isinstance(tips, list) and tips:
                print(f"      💡 Tips: {', '.join(tips[:3])}")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"\n✅ All secret places URLs have been scraped")
    print(f"✅ LLM has extracted secret place entities")
    print(f"✅ {len(items)} total secret place entities saved to InstantDB")
    print(f"✅ {len(unique_places)} unique secret places found")
    print("\nCheck InstantDB dashboard: scraped_content_secret_places collection")

if __name__ == "__main__":
    asyncio.run(scrape_secret_places_complete())
