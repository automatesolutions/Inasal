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

# Philippine phone number regex: +63 9XX XXX XXXX or 09XX XXX XXXX
PH_PHONE_REGEX = re.compile(r'^(\+63|0)?9\d{9}$')


def normalize_phone_number(phone: str) -> str:
    """Normalize Philippine phone number to +63 format"""
    # Remove spaces and dashes
    phone = re.sub(r'[\s-]', '', phone)
    # Remove leading +63 or 0
    if phone.startswith('+63'):
        phone = phone[3:]
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
    print("✅ Test endpoint called")
    return {"status": "ok", "message": "Backend is working!"}

@router.options("/send-otp")
@router.options("/verify-otp")
async def options_handler(request: Request):
    """Handle OPTIONS requests for CORS preflight - returns 200 OK"""
    print(f"🔵 OPTIONS request for {request.url.path}")
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
    print("✅ Test endpoint called")
    return {"status": "ok", "message": "Backend is working!"}

@router.post("/send-otp-phone", include_in_schema=True)
async def send_otp_phone(request: PhoneLoginRequest):
    """Send OTP to user's phone number - uses dummy OTP '000000' in dev mode"""
    import sys
    print("=" * 60, file=sys.stderr)
    print("🚀 send_otp_phone FUNCTION CALLED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    try:
        normalized_phone = normalize_phone_number(request.phone_number)
        
        print(f"\n{'='*60}")
        print(f"📨 send_otp_phone endpoint called")
        print(f"   Phone: {request.phone_number} (normalized: {normalized_phone})")
        print(f"   First Name: {request.first_name}")
        print(f"   Last Name: {request.last_name}")
        print(f"{'='*60}\n")
        
        # Always use dummy OTP "000000" for testing
        otp = "000000"
        print(f"🧪 Using fake OTP '000000' for testing")
        
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
            print(f"✅ OTP stored in Redis")
        except Exception as e:
            print(f"⚠️  Redis error (continuing anyway): {e}")
        
        print(f"\n{'='*60}")
        print(f"🔐 OTP Generated for: {normalized_phone}")
        print(f"📧 Verification Code: {otp}")
        print(f"💡 Use OTP '000000' to verify")
        print(f"{'='*60}\n")
        
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
        print(f"\n{'='*60}")
        print(f"❌ ERROR in send_otp_phone endpoint:")
        print(f"   Phone: {request.phone_number}")
        print(f"   Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Traceback:\n{error_traceback}")
        print(f"{'='*60}\n")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )


@router.post("/send-otp", include_in_schema=True)
async def send_otp(request: EmailRequest):
    """Send OTP to user's email - uses dummy OTP '000000' in dev mode"""
    import sys
    print("=" * 60, file=sys.stderr)
    print("🚀 send_otp FUNCTION CALLED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    try:
        print(f"\n{'='*60}")
        print(f"📨 send_otp endpoint called")
        print(f"   Email: {request.email}")
        print(f"   First Name: {request.first_name}")
        print(f"   Last Name: {request.last_name}")
        print(f"{'='*60}\n")
        
        # Always use dummy OTP "000000" for testing
        otp = "000000"
        print(f"🧪 Using fake OTP '000000' for testing")
        
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
            print(f"✅ OTP stored in Redis")
        except Exception as e:
            print(f"⚠️  Redis error (continuing anyway): {e}")
        
        print(f"\n{'='*60}")
        print(f"🔐 OTP Generated for: {request.email}")
        print(f"📧 Verification Code: {otp}")
        print(f"💡 Use OTP '000000' to verify")
        print(f"{'='*60}\n")
        
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
        print(f"\n{'='*60}")
        print(f"❌ ERROR in send_otp endpoint:")
        print(f"   Email: {request.email}")
        print(f"   Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Traceback:\n{error_traceback}")
        print(f"{'='*60}\n")
        
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
        print(f"\n{'='*60}")
        print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' for {normalized_phone}")
        print(f"{'='*60}\n")
    elif not stored_otp:
        if settings.dev_mode:
            if request.otp in dummy_otps:
                print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' (Redis unavailable)")
            else:
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
        if settings.dev_mode and request.otp in dummy_otps:
            print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' (stored OTP was different)")
        else:
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
    
    # Create user profile
    try:
        user_profile = await profile_service.create_profile(
            email=user_email,
            user_id=user_id,
            name=user_name,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
        )
        if user_profile:
            user_id = user_profile.user_id
            user_name = user_profile.name or user_name
    except Exception as e:
        print(f"⚠️  Failed to create profile in BigQuery: {e}")

    # Trigger background personality analysis
    async def _run_personality_analysis():
        if not user_id:
            return
        
        try:
            # Import here to avoid circular dependencies
            from app.personality_pipeline import analyze_personality_from_social_media
            
            print(f"🔍 Starting personality analysis for: {first_name} {last_name} ({normalized_phone})")
            await analyze_personality_from_social_media(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                phone_number=normalized_phone
            )
            print(f"✅ Personality analysis completed for {normalized_phone}")
        except ImportError:
            print(f"⚠️  Personality pipeline not available yet, skipping analysis")
        except Exception as exc:
            print(f"⚠️  Personality analysis failed: {exc}")

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
        print(f"\n{'='*60}")
        print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' for {request.email}")
        print(f"{'='*60}\n")
        # Continue to create user profile (code below)
    elif not stored_otp:
        # No OTP found in Redis
        if settings.dev_mode:
            # Dev mode: Allow dummy OTPs even if Redis unavailable
            if request.otp in dummy_otps:
                print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' (Redis unavailable)")
            else:
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
        if settings.dev_mode and request.otp in dummy_otps:
            # In dev mode, still accept dummy OTPs even if stored OTP is different
            print(f"🔓 DEV MODE: Accepting dummy OTP '{request.otp}' (stored OTP was different)")
        else:
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
                email=request.email,
                user_id=user_id,
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
            print(f"⚠️  Failed to create profile in BigQuery: {e}")
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
                print(f"⚠️  Failed to update profile name: {e}")

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
                print(f"🔍 Starting persona discovery via Make.com for: {final_first_name} {final_last_name} ({user_email})")
                await make_client.trigger_persona_discovery(
                    user_id,
                    final_first_name,
                    final_last_name
                )
                print(f"✅ Persona discovery triggered via Make.com for {user_email}")
                return
            except Exception as exc:
                print(f"⚠️  Make.com persona discovery failed: {exc}, falling back to LangGraph")

        # Fallback to LangGraph
        try:
            from app.persona_discovery_graph import persona_discovery_graph
            
            print(f"🔍 Starting persona discovery via LangGraph for: {final_first_name} {final_last_name} ({user_email})")

            result = await persona_discovery_graph.run(
                user_id=user_id,
                first_name=final_first_name,
                last_name=final_last_name,
            )

            print(f"✅ Persona discovery completed for {user_email}")
            print(f"   Personality traits: {result.get('personality_traits', {})}")
            print(f"   Hidden traits: {result.get('hidden_traits', {})}")
        except Exception as exc:
            print(f"⚠️  Persona discovery workflow failed: {exc}")

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

