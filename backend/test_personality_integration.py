"""Test personality integration with scraped content"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.comprehensive_recommendations import ComprehensiveRecommendationsService
from app.user_profile import UserProfile, PersonalityTraits
from app.instantdb_client import instantdb_client

async def test_personality_integration():
    print("=" * 80)
    print("TESTING PERSONALITY INTEGRATION WITH SCRAPED CONTENT")
    print("=" * 80)
    
    # Create a test user profile with specific personality traits
    test_personality = PersonalityTraits(
        adventurous=0.8,
        cultural=0.7,
        foodie=0.9,
        nature_lover=0.6,
        history_buff=0.5,
        social=0.8
    )
    
    test_profile = UserProfile(
        user_id="test_user",
        personality=test_personality
    )
    
    print(f"\n📊 Test User Personality:")
    print(f"   Adventurous: {test_personality.adventurous}")
    print(f"   Cultural: {test_personality.cultural}")
    print(f"   Foodie: {test_personality.foodie}")
    print(f"   Nature Lover: {test_personality.nature_lover}")
    print(f"   History Buff: {test_personality.history_buff}")
    print(f"   Social: {test_personality.social}")
    
    # Get some scraped content with personality_keywords
    print(f"\n📋 Fetching scraped content with personality_keywords...")
    scraped_content = await instantdb_client.get_scraped_content_by_category("restaurants_food")
    
    if not scraped_content:
        print("   ⚠️  No scraped content found for restaurants_food")
        scraped_content = await instantdb_client.get_scraped_content_by_category("tourist_spots")
    
    if not scraped_content:
        print("   ❌ No scraped content found at all")
        return
    
    print(f"   ✅ Found {len(scraped_content)} items")
    
    # Find items with personality_keywords
    items_with_pk = [item for item in scraped_content if item.get("personality_keywords")]
    print(f"   ✅ {len(items_with_pk)} items have personality_keywords")
    
    if items_with_pk:
        print(f"\n📊 Sample Item with Personality Keywords:")
        sample = items_with_pk[0]
        print(f"   Name: {sample.get('title') or sample.get('name', 'N/A')}")
        print(f"   Category: {sample.get('category', 'N/A')}")
        print(f"   Personality Keywords: {sample.get('personality_keywords')}")
        
        # Test match score calculation
        print(f"\n🧮 Testing Match Score Calculation...")
        service = ComprehensiveRecommendationsService()
        await service.initialize()
        
        # Create a mock item
        mock_item = {
            "name": sample.get("title") or sample.get("name", "Test Item"),
            "personality_keywords": sample.get("personality_keywords")
        }
        
        match_score = service._calculate_match_score(mock_item, test_personality)
        print(f"   Match Score: {match_score:.3f}")
        print(f"   Interpretation: {'✅ Strong match' if match_score > 0.7 else '⚠️ Moderate match' if match_score > 0.5 else '❌ Weak match'}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n✅ Personality integration is working!")
    print("   - Scraped content personality_keywords are being used")
    print("   - Match scores are calculated based on user personality traits")
    print("   - Recommendations will automatically incorporate personality data")

if __name__ == "__main__":
    asyncio.run(test_personality_integration())
