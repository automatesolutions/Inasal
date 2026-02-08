"""Test Bright Data SERP API with serp_api2 zone"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_serp_api():
    """Test Bright Data SERP API with the serp_api2 zone"""
    
    # Get API key from environment
    api_key = os.getenv("BRIGHT_DATA_SERP_API_KEY") or os.getenv("BRIGHT_DATA_API_TOKEN")
    
    if not api_key:
        print("[ERROR] BRIGHT_DATA_SERP_API_KEY or BRIGHT_DATA_API_TOKEN not found in .env")
        return
    
    print(f"[INFO] Using API Key: {api_key[:20]}...")
    print()
    
    # Test query
    test_query = "pizza"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Raw HTML format
    print("[TEST 1] Testing with format='raw' (HTML)")
    search_url_raw = f"https://www.google.com/search?q={test_query}"
    data_raw = {
        "zone": "serp_api2",
        "url": search_url_raw,
        "format": "raw"
    }
    print(f"       Query: {test_query}")
    print(f"       URL: {search_url_raw}")
    print()
    
    # Test 2: JSON format (if supported)
    print("[TEST 2] Testing with format='json' (structured data)")
    search_url_json = f"https://www.google.com/search?q={test_query}&brd_json=1"
    data_json = {
        "zone": "serp_api2",
        "url": search_url_json,
        "format": "json"
    }
    print(f"       Query: {test_query}")
    print(f"       URL: {search_url_json}")
    print()
    
    # Run Test 1
    print("=" * 80)
    print("TEST 1: Raw HTML Format")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Raw format
            print("[SEND] Sending request with format='raw'...")
            response_raw = await client.post(
                "https://api.brightdata.com/request",
                json=data_raw,
                headers=headers
            )
            
            print(f"[STATUS] Response Status: {response_raw.status_code}")
            print(f"[INFO] Response Type: {response_raw.headers.get('content-type', 'unknown')}")
            print(f"[INFO] Response Length: {len(response_raw.text)} characters")
            
            if response_raw.status_code == 200:
                # Check if it's HTML or JSON
                if response_raw.text.strip().startswith('<!') or response_raw.text.strip().startswith('<html'):
                    print("[RESULT] Received HTML content (raw format)")
                    print(f"         First 500 chars: {response_raw.text[:500]}...")
                else:
                    try:
                        json_data = response_raw.json()
                        print("[RESULT] Received JSON content!")
                        import json
                        print(json.dumps(json_data, indent=2)[:1000])
                    except:
                        print("[RESULT] Received text content (not JSON)")
                        print(f"         First 500 chars: {response_raw.text[:500]}...")
            else:
                print(f"[ERROR] Status {response_raw.status_code}")
                print(f"Response: {response_raw.text[:500]}")
            
            print()
            print("=" * 80)
            print("TEST 2: JSON Format")
            print("=" * 80)
            
            # Test 2: JSON format
            print("[SEND] Sending request with format='json'...")
            response_json = await client.post(
                "https://api.brightdata.com/request",
                json=data_json,
                headers=headers
            )
            
            print(f"[STATUS] Response Status: {response_json.status_code}")
            print(f"[INFO] Response Type: {response_json.headers.get('content-type', 'unknown')}")
            print(f"[INFO] Response Length: {len(response_json.text)} characters")
            
            if response_json.status_code == 200:
                # Try to parse as JSON
                try:
                    json_data = response_json.json()
                    print("[RESULT] Successfully parsed as JSON!")
                    import json
                    print(json.dumps(json_data, indent=2)[:2000])
                    if len(json.dumps(json_data, indent=2)) > 2000:
                        print("\n... (response truncated)")
                except Exception as json_error:
                    print(f"[RESULT] Could not parse as JSON: {json_error}")
                    print(f"         First 500 chars: {response_json.text[:500]}...")
            else:
                print(f"[ERROR] Status {response_json.status_code}")
                print(f"Response: {response_json.text[:500]}")
                
    except httpx.TimeoutException:
        print("[ERROR] Request timed out")
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text[:500]}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 80)
    print("Bright Data SERP API Test")
    print("=" * 80)
    print()
    asyncio.run(test_serp_api())
