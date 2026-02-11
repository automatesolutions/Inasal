"""Debug Google Sheet parsing to see why URLs are missing"""

import asyncio
import sys
import codecs
import csv

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.sheets_sync import fetch_sheet_csv, parse_sheet_csv, _normalize_header, _is_url

async def debug():
    print("=" * 80)
    print("DEBUGGING GOOGLE SHEET PARSING")
    print("=" * 80)
    
    # Fetch raw CSV
    csv_text = await fetch_sheet_csv()
    print(f"\n✅ Fetched CSV ({len(csv_text)} characters)")
    
    # Parse CSV manually to see what's happening
    reader = csv.reader(csv_text.splitlines())
    current_category = None
    
    print("\n" + "=" * 80)
    print("RAW CSV PARSING:")
    print("=" * 80)
    
    tourist_spots_rows = []
    scams_rows = []
    
    for row_num, row in enumerate(reader, 1):
        if not row:
            continue
        cell = (row[0] or "").strip()
        if not cell:
            continue
        
        # Check if it's a category header
        slug = _normalize_header(cell)
        if slug:
            current_category = slug
            print(f"\nRow {row_num}: CATEGORY HEADER -> {slug}")
            print(f"  Raw cell: '{cell}'")
            continue
        
        # Check if it's a URL
        if _is_url(cell):
            if current_category == "tourist_spots":
                tourist_spots_rows.append((row_num, cell))
            elif current_category == "scams":
                scams_rows.append((row_num, cell))
            print(f"Row {row_num}: URL ({current_category}): {cell[:80]}...")
        else:
            if current_category in ["tourist_spots", "scams"]:
                print(f"Row {row_num}: NON-URL ({current_category}): '{cell[:60]}...'")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"\nTourist Spots URLs found: {len(tourist_spots_rows)}")
    for row_num, url in tourist_spots_rows:
        print(f"  Row {row_num}: {url}")
    
    print(f"\nScams URLs found: {len(scams_rows)}")
    for row_num, url in scams_rows:
        print(f"  Row {row_num}: {url}")
    
    # Now parse using the actual function
    print("\n" + "=" * 80)
    print("PARSED USING parse_sheet_csv():")
    print("=" * 80)
    categories = parse_sheet_csv(csv_text)
    
    print(f"\nTourist Spots: {len(categories.get('tourist_spots', []))} URLs")
    for i, url in enumerate(categories.get('tourist_spots', []), 1):
        print(f"  {i}. {url}")
    
    print(f"\nScams: {len(categories.get('scams', []))} URLs")
    for i, url in enumerate(categories.get('scams', []), 1):
        print(f"  {i}. {url}")

if __name__ == "__main__":
    asyncio.run(debug())
