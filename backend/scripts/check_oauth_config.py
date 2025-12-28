#!/usr/bin/env python3
"""Quick script to check OAuth configuration"""

from app.config import settings

print("=" * 50)
print("OAuth Configuration Check")
print("=" * 50)

print("\n📋 LinkedIn OAuth:")
print(f"  Client ID: {'✅ SET' if settings.linkedin_client_id else '❌ EMPTY'}")
if settings.linkedin_client_id:
    # Show first 10 chars only for security
    masked_id = settings.linkedin_client_id[:10] + "..." if len(settings.linkedin_client_id) > 10 else settings.linkedin_client_id
    print(f"    Value: {masked_id}")
print(f"  Client Secret: {'✅ SET' if settings.linkedin_client_secret else '❌ EMPTY'}")

print("\n📋 Facebook OAuth:")
print(f"  Client ID: {'✅ SET' if settings.facebook_client_id else '❌ EMPTY'}")
print(f"  Client Secret: {'✅ SET' if settings.facebook_client_secret else '❌ EMPTY'}")

print("\n📋 Twitter OAuth:")
print(f"  Client ID: {'✅ SET' if settings.twitter_client_id else '❌ EMPTY'}")
print(f"  Client Secret: {'✅ SET' if settings.twitter_client_secret else '❌ EMPTY'}")

print("\n" + "=" * 50)
if settings.linkedin_client_id and settings.linkedin_client_secret:
    print("✅ LinkedIn OAuth is CONFIGURED!")
    print("   Restart your backend server if you just added these.")
else:
    print("❌ LinkedIn OAuth is NOT CONFIGURED")
    print("   Add LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET to .env")
print("=" * 50)

