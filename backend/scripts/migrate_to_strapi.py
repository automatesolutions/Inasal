"""Migration script: MongoDB → Strapi

This script migrates user profiles and attractions from MongoDB to Strapi CMS.
Run this after setting up Strapi and creating the content types.

Usage:
    poetry run python scripts/migrate_to_strapi.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.strapi_client import strapi_client


async def migrate_user_profiles():
    """Migrate user profiles from MongoDB to Strapi"""
    print("🔄 Starting user profiles migration...")
    
    # Connect to MongoDB
    try:
        client = AsyncIOMotorClient(settings.database_url)
        db_name = settings.database_url.split("/")[-1].split("?")[0]
        db = client[db_name]
        collection = db["user_profiles"]
        
        # Get all profiles
        profiles = await collection.find().to_list(length=None)
        print(f"📊 Found {len(profiles)} user profiles to migrate")
        
        migrated = 0
        failed = 0
        
        for profile in profiles:
            try:
                # Check if already exists in Strapi
                existing = await strapi_client.get_user_profile(profile["user_id"])
                if existing:
                    print(f"⏭️  Skipping {profile['email']} (already exists in Strapi)")
                    continue
                
                # Create in Strapi
                result = await strapi_client.create_user_profile(
                    user_id=profile["user_id"],
                    email=profile["email"],
                    name=profile.get("name"),
                    personality=profile.get("personality", {}),
                    preferences=profile.get("preferences", {}),
                )
                
                if result:
                    migrated += 1
                    print(f"✅ Migrated user: {profile['email']}")
                else:
                    failed += 1
                    print(f"❌ Failed to migrate {profile['email']}")
                    
            except Exception as e:
                failed += 1
                print(f"❌ Error migrating {profile.get('email', 'unknown')}: {e}")
        
        print(f"\n📈 Migration complete: {migrated} migrated, {failed} failed")
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False
    
    return True


async def migrate_attractions():
    """Migrate attractions from JSON file to Strapi"""
    print("\n🔄 Starting attractions migration...")
    
    attractions_file = Path(__file__).parent.parent / "data" / "attractions.json"
    
    if not attractions_file.exists():
        print(f"❌ Attractions file not found: {attractions_file}")
        return False
    
    try:
        with open(attractions_file, "r", encoding="utf-8") as f:
            attractions = json.load(f)
        
        print(f"📊 Found {len(attractions)} attractions to migrate")
        
        migrated = 0
        failed = 0
        
        for attraction in attractions:
            try:
                # Check if already exists (by name)
                existing_attrs = await strapi_client.get_attractions(
                    filters={"name": attraction["name"]}
                )
                if existing_attrs:
                    print(f"⏭️  Skipping {attraction['name']} (already exists in Strapi)")
                    continue
                
                # Prepare payload
                payload = {
                    "data": {
                        "name": attraction["name"],
                        "type": attraction["type"],
                        "description": attraction["description"],
                        "location": attraction.get("location", {}),
                        "tags": attraction.get("tags", []),
                        "best_time_to_visit": attraction.get("best_time_to_visit"),
                        "entry_fee": attraction.get("entry_fee"),
                        "personality_match": attraction.get("personality_match", {}),
                    }
                }
                
                # Create in Strapi
                response = await strapi_client.client.post(
                    f"{strapi_client.base_url}/api/attractions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {strapi_client.api_token}",
                        "Content-Type": "application/json",
                    }
                )
                response.raise_for_status()
                
                migrated += 1
                print(f"✅ Migrated attraction: {attraction['name']}")
                
            except Exception as e:
                failed += 1
                print(f"❌ Error migrating {attraction.get('name', 'unknown')}: {e}")
        
        print(f"\n📈 Migration complete: {migrated} migrated, {failed} failed")
        
    except Exception as e:
        print(f"❌ Error reading attractions file: {e}")
        return False
    
    return True


async def migrate_interaction_logs():
    """Migrate interaction logs from MongoDB to Strapi"""
    print("\n🔄 Starting interaction logs migration...")
    
    try:
        client = AsyncIOMotorClient(settings.database_url)
        db_name = settings.database_url.split("/")[-1].split("?")[0]
        db = client[db_name]
        collection = db["interaction_logs"]
        
        # Get all logs
        logs = await collection.find().to_list(length=None)
        print(f"📊 Found {len(logs)} interaction logs to migrate")
        
        migrated = 0
        failed = 0
        
        for log in logs:
            try:
                # Get user profile ID from Strapi
                profile_id = await strapi_client._get_user_profile_id(log["user_id"])
                if not profile_id:
                    print(f"⏭️  Skipping log for user {log['user_id']} (user not found in Strapi)")
                    continue
                
                # Create in Strapi
                result = await strapi_client.create_interaction_log(
                    log["user_id"],
                    log["interaction_type"],
                    log.get("content", {}),
                    log.get("metadata", {})
                )
                
                if result:
                    migrated += 1
                    if migrated % 10 == 0:
                        print(f"✅ Migrated {migrated} logs...")
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                if failed <= 5:  # Only print first few errors
                    print(f"❌ Error migrating log: {e}")
        
        print(f"\n📈 Migration complete: {migrated} migrated, {failed} failed")
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False
    
    return True


async def main():
    """Run all migrations"""
    print("🚀 Starting migration to Strapi...\n")
    
    # Check Strapi connection
    if not strapi_client.api_token:
        print("⚠️  Warning: STRAPI_API_TOKEN not set. Migration may fail.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
    
    # Run migrations
    results = []
    
    results.append(await migrate_user_profiles())
    results.append(await migrate_attractions())
    
    # Ask about interaction logs (can be large)
    print("\n❓ Migrate interaction logs? (This may take a while)")
    migrate_logs = input("Migrate interaction logs? (y/n): ")
    if migrate_logs.lower() == 'y':
        results.append(await migrate_interaction_logs())
    
    # Summary
    print("\n" + "="*50)
    print("📊 Migration Summary")
    print("="*50)
    
    if all(results):
        print("✅ All migrations completed successfully!")
    else:
        print("⚠️  Some migrations had errors. Check logs above.")
    
    # Close connections
    await strapi_client.close()
    print("\n✅ Migration script completed.")


if __name__ == "__main__":
    asyncio.run(main())

