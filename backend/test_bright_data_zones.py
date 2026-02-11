"""Test Bright Data Web Unlocker with different zone names"""

import asyncio
import sys
import codecs
import os

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.bright_data_client import bright_data_client

async def test_zones():
    print("=" * 80)
    print("TESTING BRIGHT DATA WEB UNLOCKER ZONES")
    print("=" * 80)
    
    api_key = os.getenv('BRIGHT_DATA_API_KEY') or os.getenv('BRIGHT_DATA_API_TOKEN', '')
    print(f"\nAPI Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    
    # Common zone names to try
    zones_to_test = [
        "web_unlocker",
        "webscrape_amzn",  # Your existing zone
        "web_unlocker_browser",
        "browser_automation",
    ]
    
    # Also check what's configured
    configured_zone = os.getenv('BRIGHT_DATA_WEB_UNLOCKER_ZONE', '')
    if configured_zone:
        zones_to_test.insert(0, configured_zone)
    
    print(f"\nConfigured zone: {configured_zone or 'None'}")
    print(f"\nTesting zones: {zones_to_test}")
    
    test_url = "https://www.facebook.com/BacolodFoodHunters/"
    
    for zone in zones_to_test:
        print(f"\n{'='*80}")
        print(f"Testing zone: {zone}")
        print(f"{'='*80}")
        
        try:
            # Temporarily set the zone
            original_zone = bright_data_client._web_unlocker_zone
            bright_data_client._web_unlocker_zone = zone
            
            html = await bright_data_client.scrape_with_web_unlocker(
                test_url,
                wait_for=10000,
                render=True
            )
            
            # Restore original zone
            bright_data_client._web_unlocker_zone = original_zone
            
            if html and len(html) > 100:
                print(f"✅ SUCCESS! Zone '{zone}' works!")
                print(f"   Got {len(html)} characters of HTML")
                print(f"\n   First 500 chars:")
                print(f"   {html[:500]}")
                print(f"\n   ✅ Use this zone name: {zone}")
                return zone
            else:
                print(f"   ❌ Zone '{zone}' returned empty content")
                
        except Exception as e:
            print(f"   ❌ Zone '{zone}' failed: {e}")
            continue
    
    print(f"\n{'='*80}")
    print("❌ None of the tested zones worked")
    print("=" * 80)
    print("\nPlease check your Bright Data dashboard:")
    print("1. Go to https://brightdata.com/dashboard")
    print("2. Navigate to 'Zones' or 'Web Unlocker'")
    print("3. Find your Web Unlocker zone name")
    print("4. Add it to .env as: BRIGHT_DATA_WEB_UNLOCKER_ZONE=your_zone_name")
    print("=" * 80)
    
    return None

if __name__ == "__main__":
    result = asyncio.run(test_zones())
    if result:
        print(f"\n✅ Working zone found: {result}")
        print(f"Add this to your .env file:")
        print(f"BRIGHT_DATA_WEB_UNLOCKER_ZONE={result}")
