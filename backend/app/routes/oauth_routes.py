"""OAuth authentication routes"""

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth import create_access_token
from app.oauth_providers import OAuthProviderConfig
from app.social_profile_parser import SocialProfileParser
from app.personality_inference import personality_inference_engine
from app.user_profile import UserProfileService
from app.config import settings

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])
profile_service = UserProfileService()


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request"""
    code: str
    state: Optional[str] = None


@router.get("/{provider}/authorize")
async def oauth_authorize(provider: str):
    """Initiate OAuth flow - redirects to provider"""
    config = OAuthProviderConfig.get_provider_config(provider)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    if not config.get("client_id") or not config.get("client_secret"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.capitalize()} OAuth is not configured. Please add {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET to your backend/.env file. See backend/OAUTH_SETUP.md for setup instructions.",
        )

    # Build redirect URI
    redirect_uri = f"{settings.oauth_base_url}/api/auth/oauth/{provider}/callback"

    # Get OAuth client
    client = OAuthProviderConfig.get_oauth_client(provider, redirect_uri)

    if provider.lower() == "twitter":
        # Twitter uses OAuth 1.0a - request token first
        request_token_response = await client.fetch_request_token(config["request_token_url"])
        authorize_url = client.authorize_url(config["authorize_url"])
        # Store request token in session (in production, use Redis or session storage)
        return RedirectResponse(url=authorize_url)
    else:
        # OAuth 2.0 flow
        authorize_url, state = client.create_authorization_url(config["authorize_url"])
        # Store state in session/cache for validation
        return RedirectResponse(url=authorize_url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    oauth_token: Optional[str] = Query(None),  # For Twitter OAuth 1.0a
    oauth_verifier: Optional[str] = Query(None),  # For Twitter OAuth 1.0a
):
    """Handle OAuth callback from provider"""
    config = OAuthProviderConfig.get_provider_config(provider)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    redirect_uri = f"{settings.oauth_base_url}/api/auth/oauth/{provider}/callback"

    try:
        client = OAuthProviderConfig.get_oauth_client(provider, redirect_uri)
        access_token = None
        access_token_secret = None

        if provider.lower() == "twitter":
            # Twitter OAuth 1.0a flow
            if not oauth_token or not oauth_verifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing OAuth token or verifier",
                )
            # Exchange for access token
            token_response = await client.fetch_access_token(
                config["access_token_url"],
                oauth_token=oauth_token,
                oauth_verifier=oauth_verifier,
            )
            access_token = token_response.get("oauth_token")
            access_token_secret = token_response.get("oauth_token_secret")
        else:
            # OAuth 2.0 flow
            if not code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing authorization code",
                )
            # Exchange code for access token
            token_response = await client.fetch_token(
                config["access_token_url"],
                code=code,
            )
            access_token = token_response.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to obtain access token",
            )

        # Fetch user profile from social media
        try:
            if provider.lower() == "twitter":
                social_data = await SocialProfileParser.fetch_profile(
                    provider, access_token, access_token_secret
                )
            else:
                social_data = await SocialProfileParser.fetch_profile(provider, access_token)

            # Infer personality traits from social profile
            inferred_personality = await personality_inference_engine.infer_from_social_profile(
                social_data
            )

            # Get or create user profile
            email = social_data.email
            if not email:
                # Generate a placeholder email if provider doesn't provide it
                email = f"{social_data.provider_user_id}@{provider}.oauth"

            existing_profile = await profile_service.get_profile_by_email(email)

            if existing_profile:
                # Update existing profile with OAuth info
                user_id = existing_profile.user_id
            else:
                # Create new profile
                user_id = str(uuid.uuid4())
                profile = await profile_service.create_profile(
                    email=email,
                    user_id=user_id,
                    name=social_data.name,
                )
                # Update with inferred personality
                await profile_service.update_personality(user_id, inferred_personality)

            # Auto-generate recommendations in background (fire and forget)
            try:
                from app.auto_recommendation_service import auto_recommendation_service
                profile = await profile_service.get_profile(user_id)
                if profile:
                    import asyncio
                    
                    async def _generate_recommendations():
                        try:
                            await auto_recommendation_service.generate_onboarding_recommendations(
                                user_id, profile
                            )
                        except Exception as e:
                            print(f"Error generating auto-recommendations: {e}")
                    
                    # Schedule background task
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(_generate_recommendations())
            except Exception as e:
                print(f"Note: Could not schedule auto-recommendations: {e}")

            # Create JWT token
            jwt_token = create_access_token(
                data={"sub": user_id, "email": email}
            )

            # Redirect to frontend with token (in production, use secure cookie or proper redirect)
            frontend_url = "http://localhost:3000"
            return RedirectResponse(
                url=f"{frontend_url}/auth/callback?token={jwt_token}&provider={provider}"
            )

        except Exception as e:
            print(f"Error fetching profile or creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process OAuth callback: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.get("/{provider}/status")
async def oauth_status(provider: str):
    """Check if OAuth provider is configured"""
    config = OAuthProviderConfig.get_provider_config(provider)
    if not config:
        return {"configured": False, "provider": provider}

    is_configured = bool(config.get("client_id") and config.get("client_secret"))
    return {
        "configured": is_configured,
        "provider": provider,
        "has_client_id": bool(config.get("client_id")),
    }

