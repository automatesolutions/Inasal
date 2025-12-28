"""Authentication API routes"""

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi import Response as FastAPIResponse
from pydantic import BaseModel, EmailStr
from starlette.requests import Request

from app.auth import create_access_token, generate_otp, send_otp_email
from app.redis_client import redis_client
from app.user_profile import UserProfileService
from app.strapi_client import strapi_client
from app.make_client import make_client
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
profile_service = UserProfileService()

OTP_EXPIRATION_SECONDS = 600  # 10 minutes


class EmailRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str
    first_name: str
    last_name: str


@router.options("/send-otp")
@router.options("/verify-otp")
async def options_handler(request: Request):
    """Handle OPTIONS requests for CORS preflight - returns 200 OK"""
    origin = request.headers.get("origin", "*")
    response = FastAPIResponse(status_code=200, content="")
    response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = request.headers.get("access-control-request-headers", "Content-Type, Authorization")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response


@router.post("/send-otp", include_in_schema=True)
async def send_otp(request: EmailRequest):
    """Send OTP to user's email (or bypass in dev mode)"""
    # Dev mode: Skip OTP and return token directly
    if settings.dev_mode and settings.dev_mode_bypass_otp:
        print(f"\n{'='*60}")
        print(f"🔓 DEV MODE: Skipping OTP for {request.email}")
        print(f"{'='*60}\n")
        
        import uuid
        full_name = f"{request.first_name} {request.last_name}".strip() or request.email
        
        # Try to get existing profile from MongoDB first
        user_profile = await profile_service.get_profile_by_email(request.email)
        user_id = None
        user_email = request.email
        
        if user_profile:
            user_id = user_profile.user_id
            user_email = user_profile.email
        else:
            # Create new user_id
            user_id = str(uuid.uuid4())
            # Try to create in MongoDB (may fail, that's OK)
            user_profile = await profile_service.create_profile(
                email=request.email,
                user_id=user_id,
                name=full_name,
            )
            # If MongoDB failed, user_profile will be None, but we have user_id
        
        # Use Strapi as primary source if configured
        if strapi_client.api_token:
            try:
                strapi_profile = await strapi_client.get_user_profile(user_id)
                if not strapi_profile:
                    # Create in Strapi
                    strapi_profile = await strapi_client.create_user_profile(
                        user_id=user_id,
                        email=request.email,
                        name=full_name,
                    )
                    print(f"✅ Created user profile in Strapi: {request.email}")
                else:
                    print(f"✅ Found user profile in Strapi: {request.email}")
            except Exception as e:
                print(f"⚠️  Failed to sync to Strapi: {e}")
                # Continue anyway - use user_id we generated
        
        # Generate token directly (use user_id we have)
        access_token = create_access_token(
            data={"sub": user_id, "email": user_email}
        )
        
        return {
            "message": "Login successful (dev mode - OTP bypassed)",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "email": user_email,
            "dev_mode": True,
            "dummy_otp": "000000",  # Tell frontend what dummy OTP to use
        }
    
    # Normal OTP flow
    otp = generate_otp()

    # Store OTP and user metadata in Redis with expiration (if Redis available)
    otp_key = f"otp:{request.email}"
    meta_key = f"otp:meta:{request.email}"
    
    # Try to store in Redis, but don't fail if Redis unavailable
    redis_stored = await redis_client.set(otp_key, otp, expire=OTP_EXPIRATION_SECONDS)
    await redis_client.set(
        meta_key,
        {"first_name": request.first_name, "last_name": request.last_name},
        expire=OTP_EXPIRATION_SECONDS,
    )
    
    # Always print OTP to console for testing (even if email is configured)
    print(f"\n{'='*60}")
    print(f"🔐 OTP Generated for: {request.email}")
    print(f"📧 Verification Code: {otp}")
    print(f"⏰ Expires in: {OTP_EXPIRATION_SECONDS // 60} minutes")
    if not redis_stored:
        print(f"⚠️  Redis not available - OTP stored in memory only")
    print(f"{'='*60}\n")

    await send_otp_email(request.email, otp)
    
    # In dev mode, show dummy OTP options
    response = {
        "message": "OTP sent successfully",
        "otp": otp if not settings.smtp_user else None,
    }
    if settings.dev_mode:
        response["dummy_otp"] = "000000"  # Tell frontend what dummy OTP to use
        response["dummy_otp_hint"] = "You can also use: 000000, 123456, 111111, 999999"
        print(f"💡 DEV MODE: You can use dummy OTP '000000' or '123456' to verify")
    
    return response


@router.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    """Verify OTP and return JWT token (or bypass in dev mode)"""
    # Dev mode: Skip OTP verification
    if settings.dev_mode and settings.dev_mode_bypass_otp:
        print(f"\n{'='*60}")
        print(f"🔓 DEV MODE: Skipping OTP verification for {request.email}")
        print(f"{'='*60}\n")
        
        import uuid
        full_name = f"{request.first_name} {request.last_name}".strip() or request.email
        
        # Try to get existing profile from MongoDB first
        user_profile = await profile_service.get_profile_by_email(request.email)
        user_id = None
        user_email = request.email
        
        if user_profile:
            user_id = user_profile.user_id
            user_email = user_profile.email
            # Update missing name if provided
            full_name = f"{request.first_name} {request.last_name}".strip()
            if full_name and not user_profile.name:
                await profile_service.update_name(user_profile.user_id, full_name)
        else:
            # Create new user_id
            user_id = str(uuid.uuid4())
            # Try to create in MongoDB (may fail, that's OK)
            user_profile = await profile_service.create_profile(
                email=request.email,
                user_id=user_id,
                name=full_name,
            )
            # If MongoDB failed, user_profile will be None, but we have user_id
        
        # Use Strapi as primary source if configured
        if strapi_client.api_token:
            try:
                strapi_profile = await strapi_client.get_user_profile(user_id)
                if not strapi_profile:
                    # Create in Strapi
                    strapi_profile = await strapi_client.create_user_profile(
                        user_id=user_id,
                        email=request.email,
                        name=full_name,
                    )
                    print(f"✅ Created user profile in Strapi: {request.email}")
                else:
                    print(f"✅ Found user profile in Strapi: {request.email}")
            except Exception as e:
                print(f"⚠️  Failed to sync to Strapi: {e}")
                # Continue anyway - use user_id we generated
        
        # Generate token directly (use user_id we have)
        access_token = create_access_token(
            data={"sub": user_id, "email": user_email}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "email": user_email,
            "dev_mode": True,
        }
    
    # Normal OTP verification flow
    otp_key = f"otp:{request.email}"
    meta_key = f"otp:meta:{request.email}"

    stored_otp = await redis_client.get(otp_key)

    # Dev mode: Accept dummy OTPs
    dummy_otps = ["000000", "123456", "111111", "999999"]
    if settings.dev_mode and request.otp in dummy_otps:
        print(f"\n{'='*60}")
        print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' for {request.email}")
        print(f"{'='*60}\n")
        # Continue to create user profile (code below)
    elif not stored_otp:
        if settings.dev_mode:
            # Dev mode: Allow any OTP if Redis unavailable
            print(f"⚠️  Redis unavailable - accepting OTP '{request.otp}' in dev mode for: {request.email}")
        elif not settings.smtp_user:
            # Dev mode: Allow any OTP if Redis unavailable and email not configured
            print(f"⚠️  Redis unavailable - accepting OTP '{request.otp}' in dev mode for: {request.email}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not found or expired. Please request a new OTP.",
            )
    elif stored_otp and stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP. Please try again.",
        )

    # Delete OTP after successful verification
    await redis_client.delete(otp_key)

    stored_meta = await redis_client.get(meta_key)
    if stored_meta:
        try:
            meta_data = json.loads(stored_meta)
        except (json.JSONDecodeError, TypeError):
            meta_data = {}
        await redis_client.delete(meta_key)
    else:
        meta_data = {}

    first_name = (request.first_name or meta_data.get("first_name") or "").strip()
    last_name = (request.last_name or meta_data.get("last_name") or "").strip()
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()

    # Get or create user profile (MongoDB - legacy)
    user_profile = await profile_service.get_profile_by_email(request.email)
    if not user_profile:
        user_id = str(uuid.uuid4())
        user_profile = await profile_service.create_profile(
            email=request.email,
            user_id=user_id,
            name=full_name or request.email,
        )
    else:
        # Update missing name if provided
        if not user_profile.name and full_name:
            updated = await profile_service.update_name(user_profile.user_id, full_name)
            if updated:
                user_profile = updated

    # Sync to Strapi if configured
    if strapi_client.api_token:
        try:
            strapi_profile = await strapi_client.get_user_profile(user_profile.user_id)
            if not strapi_profile:
                # Create in Strapi
                await strapi_client.create_user_profile(
                    user_id=user_profile.user_id,
                    email=user_profile.email,
                    name=user_profile.name,
                    personality=user_profile.personality.model_dump() if hasattr(user_profile.personality, 'model_dump') else user_profile.personality,
                    preferences=user_profile.preferences.model_dump() if hasattr(user_profile.preferences, 'model_dump') else user_profile.preferences,
                )
            else:
                # Update Strapi if needed
                updates = {}
                if user_profile.name and not strapi_profile.get("attributes", {}).get("name"):
                    updates["name"] = user_profile.name
                if updates:
                    await strapi_client.update_user_profile(user_profile.user_id, **updates)
        except Exception as e:
            print(f"⚠️  Failed to sync user profile to Strapi: {e}")

    # Trigger persona discovery workflow (prefer Make.com, fallback to LangGraph)
    async def _run_persona_discovery():
        # Extract name from user profile or email
        profile_name = user_profile.name or ""
        name_parts = profile_name.split() if profile_name else []
        default_first = name_parts[0] if name_parts else ""
        default_last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Use provided names, fallback to profile name, then email prefix
        final_first_name = (first_name or default_first or user_profile.email.split("@")[0] or "User").strip()
        final_last_name = (last_name or default_last or "").strip()
        
        # Try Make.com first
        if make_client.persona_webhook:
            try:
                print(f"🔍 Starting persona discovery via Make.com for: {final_first_name} {final_last_name} ({user_profile.email})")
                await make_client.trigger_persona_discovery(
                    user_profile.user_id,
                    final_first_name,
                    final_last_name
                )
                print(f"✅ Persona discovery triggered via Make.com for {user_profile.email}")
                return
            except Exception as exc:
                print(f"⚠️  Make.com persona discovery failed: {exc}, falling back to LangGraph")

        # Fallback to LangGraph
        try:
            from app.persona_discovery_graph import persona_discovery_graph
            
            print(f"🔍 Starting persona discovery via LangGraph for: {final_first_name} {final_last_name} ({user_profile.email})")

            result = await persona_discovery_graph.run(
                user_id=user_profile.user_id,
                first_name=final_first_name,
                last_name=final_last_name,
            )

            print(f"✅ Persona discovery completed for {user_profile.email}")
            print(f"   Personality traits: {result.get('personality_traits', {})}")
            print(f"   Hidden traits: {result.get('hidden_traits', {})}")
        except Exception as exc:
            print(f"⚠️  Persona discovery workflow failed: {exc}")

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_run_persona_discovery())

    access_token = create_access_token(
        data={"sub": user_profile.user_id, "email": user_profile.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_profile.user_id,
        "email": user_profile.email,
    }

