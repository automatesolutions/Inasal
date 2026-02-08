"""Authentication API routes"""

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi import Response as FastAPIResponse
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from starlette.requests import Request

from app.auth import create_access_token, generate_otp, send_otp_email
from app.redis_client import redis_client
from app.user_profile import UserProfileService
from app.make_client import make_client
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
profile_service = UserProfileService()

OTP_EXPIRATION_SECONDS = 600  # 10 minutes

# Philippine phone number regex: +63 9XX XXX XXXX, 63 9XX XXX XXXX, or 09XX XXX XXXX
PH_PHONE_REGEX = re.compile(r'^(\+63|63|0)?9\d{9}$')


def normalize_phone_number(phone: str) -> str:
    """Normalize Philippine phone number to +63 format"""
    # Remove spaces and dashes
    phone = re.sub(r'[\s-]', '', phone)
    # Remove leading +63, 63, or 0
    if phone.startswith('+63'):
        phone = phone[3:]
    elif phone.startswith('63'):
        phone = phone[2:]
    elif phone.startswith('0'):
        phone = phone[1:]
    # Add +63 prefix
    return f'+63{phone}'


class PhoneLoginRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove spaces and dashes for validation
        cleaned = re.sub(r'[\s-]', '', v)
        if not PH_PHONE_REGEX.match(cleaned):
            raise ValueError('Invalid Philippine phone number format. Use +63 9XX XXX XXXX or 09XX XXX XXXX')
        return cleaned


class EmailRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""


class PhoneOTPVerificationRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    otp: str
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r'[\s-]', '', v)
        if not PH_PHONE_REGEX.match(cleaned):
            raise ValueError('Invalid Philippine phone number format')
        return cleaned


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str
    first_name: str
    last_name: str


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify server is working"""
    return {"status": "ok", "message": "Backend is working!"}

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


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify server is working"""
    return {"status": "ok", "message": "Backend is working!"}

@router.post("/send-otp-phone", include_in_schema=True)
async def send_otp_phone(request: PhoneLoginRequest):
    """Send OTP to user's phone number - uses dummy OTP '000000' in dev mode"""
    import sys
    try:
        normalized_phone = normalize_phone_number(request.phone_number)
        
        
        # Always use dummy OTP "000000" for testing
        otp = "000000"
        
        # Try to store in Redis (but don't fail if unavailable)
        otp_key = f"otp:phone:{normalized_phone}"
        meta_key = f"otp:meta:phone:{normalized_phone}"
        
        redis_stored = False
        try:
            redis_stored = await redis_client.set(otp_key, otp, expire=OTP_EXPIRATION_SECONDS)
            await redis_client.set(
                meta_key,
                json.dumps({"first_name": request.first_name, "last_name": request.last_name, "phone_number": normalized_phone}),
                expire=OTP_EXPIRATION_SECONDS,
            )
            pass  # OTP stored in Redis
        except Exception as e:
            pass  # Redis error but continuing
        
        
        # TODO: In production, send SMS via Twilio or similar
        # For now, return success response
        return {
            "message": "OTP sent successfully (dev mode - use 000000)",
            "otp": otp,
            "dummy_otp": "000000",
            "dummy_otp_hint": "Use OTP: 000000 to verify",
            "phone_number": normalized_phone
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )


@router.post("/send-otp", include_in_schema=True)
async def send_otp(request: EmailRequest):
    """Send OTP to user's email - uses dummy OTP '000000' in dev mode"""
    import sys
    try:
        
        # Always use dummy OTP "000000" for testing
        otp = "000000"
        
        # Try to store in Redis (but don't fail if unavailable)
        otp_key = f"otp:{request.email}"
        meta_key = f"otp:meta:{request.email}"
        
        redis_stored = False
        try:
            redis_stored = await redis_client.set(otp_key, otp, expire=OTP_EXPIRATION_SECONDS)
            await redis_client.set(
                meta_key,
                {"first_name": request.first_name, "last_name": request.last_name},
                expire=OTP_EXPIRATION_SECONDS,
            )
            pass  # OTP stored in Redis
        except Exception as e:
            pass  # Redis error but continuing
        
        
        # Return success response immediately
        return {
            "message": "OTP sent successfully (dev mode - use 000000)",
            "otp": otp,
            "dummy_otp": "000000",
            "dummy_otp_hint": "Use OTP: 000000 to verify"
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_traceback = traceback.format_exc()
        
        # Return a user-friendly error message (don't expose internal error details)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )


@router.post("/verify-otp-phone")
async def verify_otp_phone(request: PhoneOTPVerificationRequest):
    """Verify OTP for phone number and return JWT token"""
    import uuid
    
    normalized_phone = normalize_phone_number(request.phone_number)
    
    # Normal OTP verification flow
    otp_key = f"otp:phone:{normalized_phone}"
    meta_key = f"otp:meta:phone:{normalized_phone}"

    stored_otp = await redis_client.get(otp_key)

    # Dev mode: Always accept dummy OTP "000000" (and other dummy OTPs for testing)
    dummy_otps = ["000000", "123456", "111111", "999999"]
    if settings.dev_mode and request.otp in dummy_otps:
        pass
    elif not stored_otp:
        if settings.dev_mode:
            if request.otp not in dummy_otps:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP not found or expired. Please request a new OTP or use 000000 in dev mode.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not found or expired. Please request a new OTP.",
            )
    elif stored_otp and stored_otp != request.otp:
        if not (settings.dev_mode and request.otp in dummy_otps):
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
    phone_number = meta_data.get("phone_number") or normalized_phone

    # Generate user_id
    user_id = str(uuid.uuid4())
    user_email = f"{normalized_phone}@phone.local"  # Placeholder email for phone users
    user_name = full_name or normalized_phone
    
    # Create user profile (email not stored in InstantDB)
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Creating profile for user_id: {user_id}, name: {user_name}, phone: {phone_number}")
        user_profile = await profile_service.create_profile(
            user_id=user_id,
            email=user_email,  # Optional, not stored in InstantDB
            name=user_name,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
        )
        if user_profile:
            user_id = user_profile.user_id
            user_name = user_profile.name or user_name
            logger.info(f"✅ Profile created successfully: {user_id}")
            # Wait a moment to ensure profile is available for queries
            import asyncio
            await asyncio.sleep(0.5)
        else:
            logger.error(f"❌ Profile creation returned None for user_id: {user_id}")
    except Exception as e:
        logger.error(f"❌ Error creating profile: {e}", exc_info=True)

    # Trigger background personality analysis (only if profile was created)
    async def _run_personality_analysis():
        if not user_id:
            logger.warning("⚠️  Skipping personality analysis: no user_id")
            return
        
        # Wait a moment for profile to be created and available
        import asyncio
        await asyncio.sleep(1.0)
        
        # Verify profile exists before starting analysis (with retries)
        profile_check = None
        for retry in range(5):
            profile_check = await profile_service.get_profile(user_id)
            if profile_check:
                logger.info(f"✅ Profile found for personality analysis (attempt {retry + 1}): {user_id}")
                break
            else:
                logger.debug(f"   Profile not found on attempt {retry + 1}, waiting...")
                await asyncio.sleep(0.5)
        
        if not profile_check:
            logger.warning(f"⚠️  Profile not found for personality analysis after 5 retries: {user_id}")
            logger.warning(f"   Will still attempt personality analysis - profile will be created if needed")
        
        try:
            logger.warning(f"🔍 STARTING personality analysis for {user_id} ({first_name} {last_name})")
            # Import here to avoid circular dependencies
            logger.warning(f"   Importing analyze_personality_from_social_media...")
            from app.personality_pipeline import analyze_personality_from_social_media
            logger.warning(f"   ✅ Import successful, calling function...")
            
            result = await analyze_personality_from_social_media(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                phone_number=normalized_phone
            )
            logger.warning(f"   ✅ Function returned: {result}")
            if result:
                logger.warning(f"✅ Personality analysis completed successfully for {user_id}")
                # Wait a moment for InstantDB to be queryable
                await asyncio.sleep(1.0)
                # Verify personality was saved
                verify_profile = await profile_service.get_profile(user_id)
                if verify_profile:
                    personality_dict = verify_profile.personality.model_dump()
                    has_traits = any(v > 0.5 for v in personality_dict.values())
                    if has_traits:
                        logger.warning(f"✅ Personality verified in profile: {personality_dict}")
                    else:
                        logger.error(f"❌ CRITICAL: Personality saved but all traits are default (0.5): {personality_dict}")
                        logger.error(f"   This means InstantDB query is not returning saved personality values!")
                else:
                    logger.error(f"❌ Failed to retrieve profile after personality analysis for {user_id}")
            else:
                logger.error(f"❌ Personality analysis returned False for {user_id}")
                logger.error(f"   This means personality analysis failed or returned no meaningful traits")
        except ImportError as ie:
            logger.error(f"❌ Import error in personality analysis: {ie}")
        except Exception as exc:
            logger.error(f"❌ Error in personality analysis for {user_id}: {exc}", exc_info=True)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_run_personality_analysis())

    # Create access token
    access_token = create_access_token(
        data={"sub": user_id, "email": user_email, "phone_number": normalized_phone}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": user_email,
        "phone_number": normalized_phone,
        "personality_analysis_status": "in_progress"
    }


@router.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    """Verify OTP and return JWT token"""
    # Always verify OTP (use dummy OTP "000000" in dev mode)
    import uuid
    
    # Normal OTP verification flow
    otp_key = f"otp:{request.email}"
    meta_key = f"otp:meta:{request.email}"

    stored_otp = await redis_client.get(otp_key)

    # Dev mode: Always accept dummy OTP "000000" (and other dummy OTPs for testing)
    dummy_otps = ["000000", "123456", "111111", "999999"]
    if settings.dev_mode and request.otp in dummy_otps:
        pass
    elif not stored_otp:
        # No OTP found in Redis
        if settings.dev_mode:
            # Dev mode: Allow dummy OTPs even if Redis unavailable
            if request.otp not in dummy_otps:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP not found or expired. Please request a new OTP or use 000000 in dev mode.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not found or expired. Please request a new OTP.",
            )
    elif stored_otp and stored_otp != request.otp:
        # OTP doesn't match
        if not (settings.dev_mode and request.otp in dummy_otps):
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

    # Get or create user profile (BigQuery)
    # Always generate a user_id first (in case BigQuery fails)
    user_id = None
    user_email = request.email
    user_name = full_name or request.email
    
    user_profile = await profile_service.get_profile_by_email(request.email)
    if not user_profile:
        user_id = str(uuid.uuid4())
        try:
            user_profile = await profile_service.create_profile(
                user_id=user_id,
                email=request.email,  # Optional, not stored in InstantDB
                name=user_name,
                first_name=first_name,
                last_name=last_name,
            )
            # If creation succeeded, use the profile's user_id
            if user_profile:
                user_id = user_profile.user_id
                user_email = user_profile.email
                user_name = user_profile.name or user_name
        except Exception as e:
            pass
            # Continue with generated user_id
    else:
        # Update missing name if provided
        user_id = user_profile.user_id
        user_email = user_profile.email
        user_name = user_profile.name or user_name
        if not user_profile.name and full_name:
            try:
                updated = await profile_service.update_name(user_profile.user_id, full_name)
                if updated:
                    user_profile = updated
                    user_name = updated.name or user_name
            except Exception as e:
                pass

    # Ensure we have a user_id (fallback if BigQuery failed)
    if not user_id:
        user_id = str(uuid.uuid4())

    # Trigger persona discovery workflow (prefer Make.com, fallback to LangGraph)
    async def _run_persona_discovery():
        if not user_id:
            return
            
        # Extract name from user profile or email
        profile_name = user_name or ""
        name_parts = profile_name.split() if profile_name else []
        default_first = name_parts[0] if name_parts else ""
        default_last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Use provided names, fallback to profile name, then email prefix
        final_first_name = (first_name or default_first or user_email.split("@")[0] or "User").strip()
        final_last_name = (last_name or default_last or "").strip()
        
        # Try Make.com first
        if make_client.persona_webhook:
            try:
                await make_client.trigger_persona_discovery(
                    user_id,
                    final_first_name,
                    final_last_name
                )
                return
            except Exception as exc:
                pass

        # Fallback to LangGraph
        try:
            from app.persona_discovery_graph import persona_discovery_graph
            
            pass

            result = await persona_discovery_graph.run(
                user_id=user_id,
                first_name=final_first_name,
                last_name=final_last_name,
            )

            pass
        except Exception as exc:
            pass

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_run_persona_discovery())

    # Create access token (always works, even if BigQuery failed)
    access_token = create_access_token(
        data={"sub": user_id, "email": user_email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": user_email,
    }

