"""Check URLs parsed from Google Sheet"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_and_parse_sheet

async def check():
    categories = await fetch_and_parse_sheet()
    
    for cat in ["tourist_spots", "dangerous_areas", "scams"]:
        urls = categories.get(cat, [])
        print(f"\n{cat.upper()}: {len(urls)} URLs")
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")

if __name__ == "__main__":
    asyncio.run(check())
