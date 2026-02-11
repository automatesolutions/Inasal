"""Debug: Check what's actually in the Google Sheet"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_sheet_csv, parse_sheet_csv

async def debug():
    print("=" * 80)
    print("DEBUGGING GOOGLE SHEET PARSING")
    print("=" * 80)
    
    csv_text = await fetch_sheet_csv()
    
    print("\n[Raw CSV - First 50 lines:]")
    lines = csv_text.splitlines()[:50]
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}: {line[:100]}")
    
    print("\n" + "=" * 80)
    print("[Parsed Categories:]")
    categories = parse_sheet_csv(csv_text)
    
    for cat, urls in categories.items():
        print(f"\n{cat}: {len(urls)} URLs")
        for url in urls:
            print(f"   - {url}")
    
    # Check for accommodation specifically
    print("\n" + "=" * 80)
    print("[Searching for accommodation-related content in CSV:]")
    csv_lower = csv_text.lower()
    if "accommodation" in csv_lower or "accomodation" in csv_lower or "hotel" in csv_lower:
        print("✅ Found accommodation/hotel keywords in CSV")
        # Find the lines
        for i, line in enumerate(csv_text.splitlines(), 1):
            line_lower = line.lower()
            if "accommodation" in line_lower or "accomodation" in line_lower:
                print(f"\nLine {i}: {line[:150]}")

if __name__ == "__main__":
    asyncio.run(debug())
