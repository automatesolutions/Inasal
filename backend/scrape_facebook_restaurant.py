"""Try scraping Facebook restaurant page with Bright Data"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.bright_data_client import bright_data_client
from app.services.entity_extractor import entity_extractor
from app.instantdb_client import instantdb_client

async def scrape_facebook():
    print("=" * 80)
    print("SCRAPING FACEBOOK RESTAURANT PAGE WITH BRIGHT DATA")
    print("=" * 80)
    
    url = "https://www.facebook.com/BacolodFoodHunters/"
    
    print(f"\n[Attempting to scrape] {url}")
    
    try:
        # Try Bright Data Web Unlocker
        if bright_data_client._api_key:
            print("\n[Using Bright Data Web Unlocker...]")
            html_content = await bright_data_client.scrape_with_web_unlocker(
                url,
                wait_for=10000  # Wait 10 seconds for JavaScript rendering
            )
            
            if html_content:
                print(f"   ✅ Got HTML content: {len(html_content)} chars")
                
                # Parse HTML to extract content
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "meta", "link"]):
                    script.decompose()
                
                # Extract text content with better formatting
                text_content = soup.get_text(separator='\n', strip=True)
                
                # Clean up excessive whitespace
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                text_content = '\n'.join(lines)
                
                print(f"   ✅ Extracted text: {len(text_content)} chars")
                print(f"   Preview (first 500 chars):\n{text_content[:500]}")
                
                if len(text_content) > 100:
                    # Create content dict for entity extraction
                    # Use more content for better extraction (Facebook pages can have lots of info)
                    content = {
                        "url": url,
                        "title": "Bacolod Food Hunters - Facebook",
                        "description": text_content[:1000],  # Longer description
                        "content_text": text_content[:12000],  # More content for LLM to analyze
                        "domain": "facebook.com",
                        "category": "restaurants_food"
                    }
                    
                    print(f"\n[Extracting restaurant entities with LLM...]")
                    entities = await entity_extractor.extract_entities(content, "restaurants_food")
                    
                    print(f"   ✅ Extracted {len(entities)} restaurant entities")
                    
                    for i, entity in enumerate(entities, 1):
                        name = entity.get("restaurant_name") or entity.get("name") or "Unknown"
                        print(f"      {i}. {name}")
                        if entity.get("address"):
                            print(f"         Address: {entity.get('address')[:60]}")
                        if entity.get("cuisine_type"):
                            print(f"         Cuisine: {entity.get('cuisine_type')}")
                    
                    # Save to InstantDB
                    if entities:
                        print(f"\n[Saving {len(entities)} restaurants to InstantDB...]")
                        collection_name = instantdb_client._get_collection_for_category("restaurants_food")
                        await instantdb_client._ensure_collection_exists(collection_name)
                        
                        saved_count = 0
                        for i, restaurant in enumerate(entities):
                            restaurant["category"] = "restaurants_food"
                            restaurant_url = f"{url}#restaurant_{i}"
                            saved = await instantdb_client.save_scraped_content(restaurant_url, restaurant)
                            if saved:
                                saved_count += 1
                                name = restaurant.get("restaurant_name") or restaurant.get("name") or "Unknown"
                                print(f"   ✅ Saved: {name}")
                        
                        print(f"\n✅ Successfully saved {saved_count}/{len(entities)} restaurants")
                else:
                    print("   ⚠️  Not enough content extracted from Facebook page")
            else:
                print("   ❌ Bright Data Web Unlocker returned no content")
        else:
            print("   ⚠️  Bright Data API key not configured")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(scrape_facebook())
