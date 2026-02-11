"""Check what URLs are in the Google Sheet for secret places"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_and_parse_sheet

async def check_urls():
    categories = await fetch_and_parse_sheet()
    secret_places = categories.get("secret_places", [])
    
    print(f"\nSecret Places URLs from Google Sheet: {len(secret_places)}")
    print("=" * 80)
    for i, url in enumerate(secret_places, 1):
        print(f"{i}. {url}")
    print("=" * 80)
    
    # Also check all categories
    print("\nAll categories and their URL counts:")
    for cat, urls in categories.items():
        print(f"  {cat}: {len(urls)} URLs")

if __name__ == "__main__":
    asyncio.run(check_urls())
