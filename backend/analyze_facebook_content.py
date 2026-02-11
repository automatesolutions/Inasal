"""Analyze Facebook page content to find restaurant mentions"""

import asyncio
import sys
import codecs
import re

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.bright_data_client import bright_data_client
from bs4 import BeautifulSoup

async def analyze():
    url = "https://www.facebook.com/BacolodFoodHunters/"
    
    print("Scraping Facebook page...")
    html_content = await bright_data_client.scrape_with_web_unlocker(url)
    
    if not html_content:
        print("Failed to scrape")
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove scripts and styles
    for script in soup(["script", "style", "meta", "link"]):
        script.decompose()
    
    # Get all text
    text = soup.get_text(separator='\n', strip=True)
    lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 3]
    
    print(f"\nTotal lines: {len(lines)}")
    print(f"\nFirst 100 lines:")
    for i, line in enumerate(lines[:100], 1):
        print(f"{i:3d}: {line[:100]}")
    
    # Look for restaurant-like patterns
    print(f"\n{'='*80}")
    print("Looking for restaurant mentions...")
    print(f"{'='*80}")
    
    restaurant_keywords = ['restaurant', 'cafe', 'eatery', 'food', 'dining', 'bakery', 'grill', 'bar', 'bistro']
    restaurant_lines = []
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in restaurant_keywords):
            if len(line) > 10 and len(line) < 200:  # Reasonable length
                restaurant_lines.append(line)
    
    print(f"\nFound {len(restaurant_lines)} lines with restaurant keywords:")
    for i, line in enumerate(restaurant_lines[:50], 1):
        print(f"{i:3d}: {line}")

if __name__ == "__main__":
    asyncio.run(analyze())
