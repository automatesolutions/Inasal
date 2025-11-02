"""Test core functionality without LangChain dependencies"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_core_imports():
    """Test that core modules can be imported"""
    print("🧪 Testing Core Module Imports...\n")
    
    try:
        from app.config import settings
        print("✅ Config module imported")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from app.auth import generate_otp, create_access_token
        print("✅ Auth module imported")
    except Exception as e:
        print(f"❌ Auth import failed: {e}")
        return False
    
    try:
        from app.user_profile import UserProfile, PersonalityTraits, UserPreferences
        print("✅ User profile module imported")
    except Exception as e:
        print(f"❌ User profile import failed: {e}")
        return False
    
    try:
        from app.database import get_database
        print("✅ Database module imported")
    except Exception as e:
        print(f"❌ Database import failed: {e}")
        return False
    
    try:
        from app.redis_client import redis_client
        print("✅ Redis client imported")
    except Exception as e:
        print(f"❌ Redis client import failed: {e}")
        return False
    
    print("\n✅ All core modules imported successfully!")
    return True


async def test_auth_functions():
    """Test auth functions"""
    print("\n🧪 Testing Auth Functions...\n")
    
    try:
        from app.auth import generate_otp, create_access_token, decode_access_token
        
        # Test OTP generation
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
        print(f"✅ OTP generation: {otp}")
        
        # Test token creation
        token = create_access_token({"sub": "test-user", "email": "test@example.com"})
        assert token is not None
        print("✅ Token creation works")
        
        # Test token decoding
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test-user"
        print("✅ Token decoding works")
        
        return True
    except Exception as e:
        print(f"❌ Auth function test failed: {e}")
        return False


async def test_user_profile_models():
    """Test user profile models"""
    print("\n🧪 Testing User Profile Models...\n")
    
    try:
        from app.user_profile import UserProfile, PersonalityTraits, UserPreferences
        
        # Test personality traits
        traits = PersonalityTraits(adventurous=0.8, cultural=0.7)
        assert traits.adventurous == 0.8
        print("✅ PersonalityTraits model works")
        
        # Test preferences
        prefs = UserPreferences(budget_range="mid-range", interests=["food", "culture"])
        assert prefs.budget_range == "mid-range"
        assert "food" in prefs.interests
        print("✅ UserPreferences model works")
        
        # Test profile
        profile = UserProfile(
            user_id="test-123",
            email="test@example.com",
            personality=traits,
            preferences=prefs
        )
        assert profile.user_id == "test-123"
        print("✅ UserProfile model works")
        
        return True
    except Exception as e:
        print(f"❌ User profile model test failed: {e}")
        return False


async def main():
    """Run all core tests"""
    print("=" * 60)
    print("🧪 Core Functionality Tests (Without LangChain)")
    print("=" * 60)
    
    results = {}
    
    results["imports"] = await test_core_imports()
    results["auth"] = await test_auth_functions()
    results["models"] = await test_user_profile_models()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:15} {status}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All core tests passed! Basic functionality is working.")
        print("\nNote: LangChain features (recommendations, chat, RAG) require")
        print("      additional dependencies that may need separate installation.")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

