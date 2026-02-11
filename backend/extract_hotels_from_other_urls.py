"""Extract hotels from tourist_spots URLs (hotels might be mentioned there)"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet
from app.content_scraper import ContentScraper
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def extract_hotels():
    print("=" * 80)
    print("EXTRACTING HOTELS FROM TOURIST SPOTS URLS")
    print("=" * 80)
    print("\nSince there are no accommodation_hotels URLs in the sheet,")
    print("we'll check tourist_spots URLs for hotel mentions...\n")
    
    categories = await fetch_and_parse_sheet()
    tourist_urls = categories.get("tourist_spots", [])
    
    print(f"Checking {len(tourist_urls)} tourist_spots URLs for hotel mentions...\n")
    
    scraper = ContentScraper()
    hotels_found = []
    
    for url in tourist_urls[:5]:  # Check first 5 URLs
        if "facebook.com" in url.lower() or "reddit.com" in url.lower():
            continue
        
        print(f"[Checking] {url[:70]}...")
        content = await scraper.scrape_url(url, "tourist_spots")
        
        if not content:
            continue
        
        # Check if content mentions hotels
        text = content.get("content_text", "").lower()
        hotel_keywords = ["hotel", "accommodation", "resort", "inn", "hostel", "l'fisher", "seda", "go hotels"]
        
        mentions_hotels = any(keyword in text for keyword in hotel_keywords)
        
        if mentions_hotels:
            print(f"   ✅ Mentions hotels! Extracting...")
            # Extract hotels from this content
            entities = await entity_extractor.extract_entities(content, "accommodation_hotels")
            
            if entities and len(entities) > 0:
                print(f"   ✅ Extracted {len(entities)} hotel entities")
                for entity in entities:
                    name = entity.get("hotel_name") or entity.get("name") or "Unknown"
                    print(f"      - {name}")
                    hotels_found.extend(entities)
            else:
                print(f"   ⚠️  No hotels extracted")
        else:
            print(f"   ❌ No hotel mentions")
    
        # Save hotels to accommodation_hotels collection
    if hotels_found:
        print(f"\n[Saving {len(hotels_found)} hotels to InstantDB...]")
        collection_name = instantdb_client._get_collection_for_category("accommodation_hotels")
        await instantdb_client._ensure_collection_exists(collection_name)
        
        saved_count = 0
        for i, hotel in enumerate(hotels_found):
            # Set category to accommodation_hotels
            hotel["category"] = "accommodation_hotels"
            hotel_url = f"extracted_from_tourist_spots#hotel_{i}"
            saved = await instantdb_client.save_scraped_content(hotel_url, hotel)
            if saved:
                saved_count += 1
        
        print(f"✅ Saved {saved_count}/{len(hotels_found)} hotels")
    else:
        print("\n⚠️  No hotels found in tourist_spots URLs")
        print("   You need to add hotel URLs to the Google Sheet under 'Accommodation & Hotels' section")
    
    # Verify
    await asyncio.sleep(3)
    items = await instantdb_client.get_scraped_content_by_category("accommodation_hotels")
    print(f"\n✅ Total hotels in InstantDB: {len(items)}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(extract_hotels())
