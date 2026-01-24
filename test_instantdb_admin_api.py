#!/usr/bin/env python3
"""Test updated InstantDB client with correct HTTP API"""

import os
import sys
import asyncio
import httpx
import json
import time
import uuid
from dotenv import load_dotenv
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
env_path = backend_dir / ".env"

load_dotenv(env_path)

app_id = os.getenv("INSTANTDB_APP_ID")
admin_token = os.getenv("INSTANTDB_ADMIN_TOKEN")

if not app_id or not admin_token:
    print("ERROR - Credentials not found!")
    sys.exit(1)

print(f"App ID: {app_id[:20]}...")
print(f"Admin Token: {admin_token[:20]}...")
print()

async def test_admin_api():
    """Test InstantDB Admin API (correct endpoints)"""
    
    base_url = "https://api.instantdb.com"
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "App-Id": app_id,
        "Content-Type": "application/json"
    }
    
    test_user_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        print("=" * 70)
        print("1. TEST: Write a new user profile using /admin/transact")
        print("=" * 70)
        
        write_url = f"{base_url}/admin/transact"
        write_payload = {
            "steps": [
                [
                    "update",
                    "user_profiles",
                    test_user_id,
                    {
                        "id": test_user_id,
                        "name": "Test User",
                        "email": "test@example.com",
                        "adventurous": 0.75,
                        "cultural": 0.80,
                        "foodie": 0.65,
                        "created_at": "2026-01-24T00:00:00",
                    }
                ]
            ]
        }
        
        print(f"URL: {write_url}")
        print(f"Payload: {json.dumps(write_payload, indent=2)}")
        print()
        
        write_response = await client.post(write_url, json=write_payload, headers=headers)
        print(f"Status: {write_response.status_code}")
        print(f"Response: {write_response.text}")
        print()
        
        if write_response.status_code not in [200, 201]:
            print("ERROR - Write failed!")
            return
        
        print("SUCCESS - User profile written!")
        print()
        
        # Wait a moment for data to persist
        await asyncio.sleep(1)
        
        print("=" * 70)
        print("2. TEST: Read the user profile back using /admin/query")
        print("=" * 70)
        
        read_url = f"{base_url}/admin/query"
        read_payload = {
            "query": {
                "user_profiles": {
                    "$": {
                        "where": {
                            "id": test_user_id
                        }
                    }
                }
            }
        }
        
        print(f"URL: {read_url}")
        print(f"Payload: {json.dumps(read_payload, indent=2)}")
        print()
        
        read_response = await client.post(read_url, json=read_payload, headers=headers)
        print(f"Status: {read_response.status_code}")
        print(f"Response: {read_response.text}")
        print()
        
        if read_response.status_code == 200 and read_response.text:
            try:
                data = read_response.json()
                print(f"Parsed Response:")
                print(json.dumps(data, indent=2))
                
                if "user_profiles" in data and len(data["user_profiles"]) > 0:
                    profile = data["user_profiles"][0]
                    print()
                    print("SUCCESS - User profile retrieved!")
                    print(f"Profile: {json.dumps(profile, indent=2)}")
                else:
                    print("ERROR - No user_profiles in response")
            except json.JSONDecodeError as e:
                print(f"ERROR - Could not parse JSON: {e}")
        else:
            print("ERROR - No data returned or bad status")
        print()
        
        print("=" * 70)
        print("3. TEST: Update personality traits")
        print("=" * 70)
        
        update_payload = {
            "steps": [
                [
                    "update",
                    "user_profiles",
                    test_user_id,
                    {
                        "id": test_user_id,
                        "name": "Test User",
                        "email": "test@example.com",
                        "adventurous": 0.95,
                        "cultural": 0.85,
                        "foodie": 0.70,
                        "social": 0.88,
                        "updated_at": "2026-01-24T01:00:00",
                    }
                ]
            ]
        }
        
        print(f"Payload: {json.dumps(update_payload, indent=2)}")
        print()
        
        update_response = await client.post(write_url, json=update_payload, headers=headers)
        print(f"Status: {update_response.status_code}")
        print(f"Response: {update_response.text}")
        print()
        
        if update_response.status_code in [200, 201]:
            print("SUCCESS - User profile updated!")
        print()

# Run tests
print("Testing InstantDB Admin HTTP API")
print("=" * 70)
print()

asyncio.run(test_admin_api())

print("=" * 70)
print("Test Complete!")
print("=" * 70)
