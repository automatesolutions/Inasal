"""Social media profile data extraction and parsing"""

from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.oauth_providers import OAuthProviderConfig


class SocialProfileData(BaseModel):
    """Extracted social media profile data"""

    provider: str
    provider_user_id: str
    name: str
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    profile_picture: Optional[str] = None
    interests: List[str] = []
    posts_content: List[str] = []  # Recent posts/tweets
    work_history: List[Dict] = []  # LinkedIn
    education: List[Dict] = []
    friends_count: Optional[int] = None  # Facebook/LinkedIn
    followers_count: Optional[int] = None  # Twitter


class SocialProfileParser:
    """Parser for extracting social media profile data"""

    @staticmethod
    async def fetch_facebook_profile(access_token: str) -> SocialProfileData:
        """Fetch Facebook profile data"""
        config = OAuthProviderConfig.get_provider_config("facebook")
        if not config:
            raise ValueError("Facebook OAuth not configured")

        async with httpx.AsyncClient() as client:
            # Get basic profile info
            profile_response = await client.get(
                f"{config['api_base_url']}/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name,email,bio,location,hometown",
                },
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()

            # Get profile picture
            picture_response = await client.get(
                f"{config['api_base_url']}/me/picture",
                params={"access_token": access_token, "type": "large", "redirect": "0"},
            )
            picture_url = None
            if picture_response.status_code == 200:
                picture_data = picture_response.json()
                picture_url = picture_data.get("data", {}).get("url")

            # Get user likes/interests (limited to 10)
            likes_response = await client.get(
                f"{config['api_base_url']}/me/likes",
                params={"access_token": access_token, "limit": 10},
            )
            interests = []
            if likes_response.status_code == 200:
                likes_data = likes_response.json()
                interests = [like.get("name", "") for like in likes_data.get("data", [])]

            # Get recent posts (limited to 5)
            posts_response = await client.get(
                f"{config['api_base_url']}/me/posts",
                params={"access_token": access_token, "limit": 5, "fields": "message"},
            )
            posts_content = []
            if posts_response.status_code == 200:
                posts_data = posts_response.json()
                posts_content = [
                    post.get("message", "")
                    for post in posts_data.get("data", [])
                    if post.get("message")
                ]

            return SocialProfileData(
                provider="facebook",
                provider_user_id=profile_data.get("id", ""),
                name=profile_data.get("name", ""),
                email=profile_data.get("email"),
                bio=profile_data.get("bio"),
                location=profile_data.get("location", {}).get("name") if profile_data.get("location") else None,
                profile_picture=picture_url,
                interests=interests,
                posts_content=posts_content,
            )

    @staticmethod
    async def fetch_twitter_profile(access_token: str, access_token_secret: str) -> SocialProfileData:
        """Fetch Twitter/X profile data"""
        config = OAuthProviderConfig.get_provider_config("twitter")
        if not config:
            raise ValueError("Twitter OAuth not configured")

        # Note: Twitter OAuth 2.0 uses bearer tokens, OAuth 1.0a uses token + secret
        # For simplicity, we'll use OAuth 2.0 bearer token approach
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            # Get user profile
            profile_response = await client.get(
                f"{config['api_base_url']}/users/me",
                params={"user.fields": "description,location,profile_image_url"},
                headers=headers,
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()

            # Get recent tweets (limited to 5)
            tweets_response = await client.get(
                f"{config['api_base_url']}/users/me/tweets",
                params={"max_results": 5, "tweet.fields": "text"},
                headers=headers,
            )
            tweets_content = []
            if tweets_response.status_code == 200:
                tweets_data = tweets_response.json()
                tweets_content = [
                    tweet.get("text", "")
                    for tweet in tweets_data.get("data", [])
                    if tweet.get("text")
                ]

            user_data = profile_data.get("data", {})
            return SocialProfileData(
                provider="twitter",
                provider_user_id=user_data.get("id", ""),
                name=user_data.get("name", ""),
                email=None,  # Twitter API doesn't provide email without additional permissions
                bio=user_data.get("description"),
                location=user_data.get("location"),
                profile_picture=user_data.get("profile_image_url"),
                posts_content=tweets_content,
                followers_count=None,  # Would need additional API call
            )

    @staticmethod
    async def fetch_linkedin_profile(access_token: str) -> SocialProfileData:
        """Fetch LinkedIn profile data"""
        config = OAuthProviderConfig.get_provider_config("linkedin")
        if not config:
            raise ValueError("LinkedIn OAuth not configured")

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            # Get basic profile info
            profile_response = await client.get(
                f"{config['api_base_url']}/me",
                headers=headers,
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()

            # Get email
            email_response = await client.get(
                f"{config['api_base_url']}/emailAddress?q=members&projection=(elements*(handle~))",
                headers=headers,
            )
            email = None
            if email_response.status_code == 200:
                email_data = email_response.json()
                elements = email_data.get("elements", [])
                if elements:
                    email = elements[0].get("handle~", {}).get("emailAddress")

            # Get profile with additional fields
            profile_fields_response = await client.get(
                f"{config['api_base_url']}/me?projection=(id,localizedFirstName,localizedLastName,headline,location)",
                headers=headers,
            )
            full_profile = {}
            if profile_fields_response.status_code == 200:
                full_profile = profile_fields_response.json()

            # Get work history (simplified - would need additional API calls for full details)
            work_history = []

            # Get education (simplified)
            education = []

            first_name = full_profile.get("localizedFirstName", "")
            last_name = full_profile.get("localizedLastName", "")
            name = f"{first_name} {last_name}".strip()

            return SocialProfileData(
                provider="linkedin",
                provider_user_id=profile_data.get("id", ""),
                name=name,
                email=email,
                bio=full_profile.get("headline"),
                location=full_profile.get("location", {}).get("name") if full_profile.get("location") else None,
                work_history=work_history,
                education=education,
            )

    @staticmethod
    async def fetch_profile(provider: str, access_token: str, access_token_secret: Optional[str] = None) -> SocialProfileData:
        """Fetch profile data from any provider"""
        if provider.lower() == "facebook":
            return await SocialProfileParser.fetch_facebook_profile(access_token)
        elif provider.lower() == "twitter":
            if not access_token_secret:
                raise ValueError("Twitter requires access_token_secret")
            return await SocialProfileParser.fetch_twitter_profile(access_token, access_token_secret)
        elif provider.lower() == "linkedin":
            return await SocialProfileParser.fetch_linkedin_profile(access_token)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

