"""Scrape Tourist Spots, Dangerous Areas, and Scams URLs from Google Sheet"""

import asyncio
import sys
import codecs
import logging

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

logging.basicConfig(level=logging.INFO)

from app.sheets_sync import fetch_and_parse_sheet, scrape_all_urls_from_sheet
from app.instantdb_client import instantdb_client

async def scrape_all_categories():
    print("=" * 80)
    print("SCRAPING TOURIST SPOTS, DANGEROUS AREAS, AND SCAMS")
    print("=" * 80)
    print("\nThis will:")
    print("1. Fetch URLs from Google Sheet for all three categories")
    print("2. Scrape each URL with Bright Data Web Unlocker")
    print("3. Use LLM to extract ALL entities mentioned")
    print("4. Save each entity as a separate record to InstantDB")
    print("=" * 80)
    
    # Get URLs from sheet
    categories = await fetch_and_parse_sheet()
    
    target_categories = {
        "tourist_spots": categories.get("tourist_spots", []),
        "dangerous_areas": categories.get("dangerous_areas", []),
        "scams": categories.get("scams", [])
    }
    
    print(f"\n📋 URLs to scrape:")
    for cat, urls in target_categories.items():
        print(f"   {cat}: {len(urls)} URLs")
        for i, url in enumerate(urls[:5], 1):  # Show first 5
            print(f"      {i}. {url[:80]}...")
        if len(urls) > 5:
            print(f"      ... and {len(urls) - 5} more")
    
    total_urls = sum(len(urls) for urls in target_categories.values())
    if total_urls == 0:
        print("\n❌ No URLs found for these categories!")
        return
    
    # Scrape all URLs
    print(f"\n{'='*80}")
    print(f"SCRAPING {total_urls} URLS ACROSS 3 CATEGORIES...")
    print(f"{'='*80}\n")
    
    results = await scrape_all_urls_from_sheet(
        target_categories,
        max_concurrent=3
    )
    
    print(f"\n✅ Scraping completed!")
    for cat, cat_results in results.items():
        print(f"   {cat}: {len(cat_results)} URLs scraped")
    
    # Verify in InstantDB
    print(f"\n{'='*80}")
    print("VERIFYING INSTANTDB...")
    print(f"{'='*80}")
    await asyncio.sleep(5)  # Wait for propagation
    
    summary = {}
    for category in ["tourist_spots", "dangerous_areas", "scams"]:
        items = await instantdb_client.get_scraped_content_by_category(category)
        summary[category] = {
            "total": len(items),
            "unique": {}
        }
        
        # Count unique items
        for item in items:
            name = item.get("attraction_name") or item.get("name") or item.get("title", "Unknown")
            if name and name != "Unknown":
                if name not in summary[category]["unique"]:
                    summary[category]["unique"][name] = item
        
        summary[category]["unique_count"] = len(summary[category]["unique"])
    
    print(f"\n📊 RESULTS SUMMARY:")
    print(f"{'='*80}")
    for category, data in summary.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        print(f"   Total entities: {data['total']}")
        print(f"   Unique items: {data['unique_count']}")
        
        # Show sample items
        print(f"\n   Sample items:")
        for i, (name, item) in enumerate(sorted(data["unique"].items())[:5], 1):
            print(f"      {i}. {name[:60]}")
            if item.get("address") or item.get("location"):
                loc = item.get("address") or item.get("location", "")
                if loc:
                    print(f"         📍 {str(loc)[:70]}")
            if item.get("description"):
                desc = str(item.get("description", ""))[:100]
                if desc:
                    print(f"         📝 {desc}...")
            if category == "scams" and item.get("scam_type"):
                print(f"         ⚠️  Type: {item.get('scam_type')}")
            if category == "dangerous_areas" and item.get("severity"):
                print(f"         ⚠️  Severity: {item.get('severity')}")
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"\n✅ All URLs have been scraped")
    print(f"✅ LLM has extracted entities for each category")
    print(f"\n📊 Final Counts:")
    for category, data in summary.items():
        print(f"   {category}: {data['total']} entities ({data['unique_count']} unique)")
    print("\nCheck InstantDB dashboard for:")
    print("   - scraped_content_tourist_spots")
    print("   - scraped_content_dangerous_areas")
    print("   - scraped_content_scams")

if __name__ == "__main__":
    asyncio.run(scrape_all_categories())
