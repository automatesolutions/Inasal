"""Script to test API endpoints and verify the system is working"""

import asyncio
import httpx
import json
from typing import Optional


BASE_URL = "http://localhost:8000"


class APITester:
    """Test API endpoints"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None

    async def test_health_check(self) -> bool:
        """Test health check endpoint"""
        print("\n🔍 Testing Health Check...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    print(f"✅ Health check passed: {response.json()}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    async def test_send_otp(self, email: str = "test@example.com") -> bool:
        """Test sending OTP"""
        print(f"\n🔍 Testing Send OTP for {email}...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/send-otp",
                    json={"email": email},
                )
                if response.status_code == 200:
                    print(f"✅ OTP sent successfully: {response.json()}")
                    return True
                else:
                    print(f"❌ OTP send failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ OTP send error: {e}")
            return False

    async def test_verify_otp(
        self, email: str = "test@example.com", otp: str = "123456"
    ) -> bool:
        """Test OTP verification (will fail with wrong OTP, but tests endpoint)"""
        print(f"\n🔍 Testing OTP Verification...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/verify-otp",
                    json={"email": email, "otp": otp},
                )
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    print(f"✅ OTP verified successfully")
                    print(f"   User ID: {self.user_id}")
                    print(f"   Token: {self.token[:20]}...")
                    return True
                else:
                    print(f"⚠️  OTP verification failed (expected with wrong OTP): {response.status_code}")
                    print(f"   Note: You need to use a real OTP from the send-otp response")
                    return False
        except Exception as e:
            print(f"❌ OTP verification error: {e}")
            return False

    async def test_get_profile(self) -> bool:
        """Test getting user profile"""
        if not self.token:
            print("\n⚠️  Skipping profile test - no authentication token")
            return False

        print("\n🔍 Testing Get Profile...")
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/profile/me", headers=headers
                )
                if response.status_code == 200:
                    profile = response.json()
                    print(f"✅ Profile retrieved successfully")
                    print(f"   Email: {profile.get('profile', {}).get('email')}")
                    print(f"   User ID: {profile.get('profile', {}).get('user_id')}")
                    return True
                else:
                    print(f"❌ Get profile failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Get profile error: {e}")
            return False

    async def test_get_recommendations(self) -> bool:
        """Test getting recommendations"""
        if not self.token:
            print("\n⚠️  Skipping recommendations test - no authentication token")
            return False

        print("\n🔍 Testing Get Recommendations...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(
                    f"{self.base_url}/api/recommendations/?limit=5", headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    count = data.get("count", 0)
                    print(f"✅ Recommendations retrieved successfully")
                    print(f"   Count: {count}")
                    if data.get("recommendations"):
                        first = data["recommendations"][0]
                        print(f"   First recommendation: {first.get('name')}")
                        if "weather_context" in first:
                            print(f"   ✅ Weather context included")
                    return True
                else:
                    print(f"❌ Get recommendations failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Get recommendations error: {e}")
            return False

    async def test_get_weather(self) -> bool:
        """Test getting weather"""
        print("\n🔍 Testing Get Weather...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/rag/weather")
                if response.status_code == 200:
                    data = response.json()
                    weather = data.get("weather", {})
                    print(f"✅ Weather retrieved successfully")
                    print(f"   Location: {weather.get('location')}")
                    print(f"   Temperature: {weather.get('temperature')}°C")
                    print(f"   Condition: {weather.get('condition')}")
                    return True
                else:
                    print(f"❌ Get weather failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Get weather error: {e}")
            return False

    async def test_get_events(self) -> bool:
        """Test getting events"""
        print("\n🔍 Testing Get Events...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/rag/events")
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    count = data.get("count", 0)
                    print(f"✅ Events retrieved successfully")
                    print(f"   Count: {count}")
                    if events:
                        print(f"   First event: {events[0].get('title')}")
                    return True
                else:
                    print(f"❌ Get events failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Get events error: {e}")
            return False

    async def test_get_local_tips(self) -> bool:
        """Test getting local tips"""
        print("\n🔍 Testing Get Local Tips...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/rag/local-tips",
                    json={"query": "What should I pack for Bacolod?"},
                )
                if response.status_code == 200:
                    data = response.json()
                    tip = data.get("tip", "")
                    print(f"✅ Local tips retrieved successfully")
                    print(f"   Tip: {tip[:100]}...")
                    return True
                else:
                    print(f"❌ Get local tips failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Get local tips error: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🚀 Starting API Endpoint Tests")
        print("=" * 60)

        results = {}

        # Basic connectivity tests
        results["health"] = await self.test_health_check()
        results["weather"] = await self.test_get_weather()
        results["events"] = await self.test_get_events()

        # Auth tests
        results["send_otp"] = await self.test_send_otp()
        
        # Note: OTP verification requires a real OTP, so we just test the endpoint
        # In real usage, you'd get the OTP from email/console and use it here
        print("\n💡 Tip: To test OTP verification, check the console output or email")
        print("   for the OTP code, then verify it manually.")

        # Protected endpoints (require auth)
        if self.token:
            results["profile"] = await self.test_get_profile()
            results["recommendations"] = await self.test_get_recommendations()
        else:
            print("\n⚠️  Skipping protected endpoint tests - need valid auth token")

        # RAG tests
        results["local_tips"] = await self.test_get_local_tips()

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"Passed: {passed}/{total}")

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name:20} {status}")

        print("\n" + "=" * 60)
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        print("=" * 60)


async def main():
    """Main test function"""
    tester = APITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("API Endpoint Tester")
    print("=" * 60)
    print("\n⚠️  Make sure the backend server is running:")
    print("   pnpm --filter backend dev")
    print("\nPress Ctrl+C to cancel, or wait 3 seconds to continue...\n")
    
    try:
        import time
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled")
        exit(0)

    asyncio.run(main())

