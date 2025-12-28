"""OAuth provider configuration and utilities"""

from typing import Dict, Optional
from authlib.integrations.httpx_client import AsyncOAuth2Client, AsyncOAuth1Client
import httpx

from app.config import settings


class OAuthProviderConfig:
    """OAuth provider configurations"""

    FACEBOOK = {
        "name": "facebook",
        "authorize_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "access_token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "api_base_url": "https://graph.facebook.com/v18.0",
        "scopes": ["email", "public_profile"],
        "client_id": settings.facebook_client_id,
        "client_secret": settings.facebook_client_secret,
    }

    TWITTER = {
        "name": "twitter",
        "request_token_url": "https://api.twitter.com/oauth/request_token",
        "authorize_url": "https://api.twitter.com/oauth/authorize",
        "access_token_url": "https://api.twitter.com/oauth/access_token",
        "api_base_url": "https://api.twitter.com/2",
        "scopes": ["tweet.read", "users.read"],
        "client_id": settings.twitter_client_id,
        "client_secret": settings.twitter_client_secret,
    }

    LINKEDIN = {
        "name": "linkedin",
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "access_token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "api_base_url": "https://api.linkedin.com/v2",
        "scopes": ["r_liteprofile", "r_emailaddress"],
        "client_id": settings.linkedin_client_id,
        "client_secret": settings.linkedin_client_secret,
    }

    @classmethod
    def get_provider_config(cls, provider_name: str) -> Optional[Dict]:
        """Get OAuth configuration for a provider"""
        provider_map = {
            "facebook": cls.FACEBOOK,
            "twitter": cls.TWITTER,
            "linkedin": cls.LINKEDIN,
        }
        return provider_map.get(provider_name.lower())

    @classmethod
    def get_oauth_client(cls, provider_name: str, redirect_uri: str):
        """Get OAuth client for a provider"""
        config = cls.get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Unknown provider: {provider_name}")

        if provider_name.lower() == "twitter":
            # Twitter uses OAuth 1.0a
            return AsyncOAuth1Client(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                redirect_uri=redirect_uri,
            )
        else:
            # Facebook and LinkedIn use OAuth 2.0
            return AsyncOAuth2Client(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                redirect_uri=redirect_uri,
                scope=config.get("scopes", []),
            )

