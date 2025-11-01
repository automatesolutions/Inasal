"""Authentication API routes"""

import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.auth import send_otp_email, generate_otp, create_access_token
from app.redis_client import redis_client
from app.user_profile import UserProfileService

router = APIRouter(prefix="/api/auth", tags=["auth"])
profile_service = UserProfileService()

OTP_EXPIRATION_SECONDS = 600  # 10 minutes


class EmailRequest(BaseModel):
    email: EmailStr


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str


@router.post("/send-otp")
async def send_otp(request: EmailRequest):
    """Send OTP to user's email"""
    otp = generate_otp()
    
    # Store OTP in Redis with expiration
    otp_key = f"otp:{request.email}"
    await redis_client.set(otp_key, otp, expire=OTP_EXPIRATION_SECONDS)
    
    await send_otp_email(request.email, otp)
    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    """Verify OTP and return JWT token"""
    # Get OTP from Redis
    otp_key = f"otp:{request.email}"
    stored_otp = await redis_client.get(otp_key)
    
    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or expired. Please request a new OTP.",
        )
    
    if stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP. Please try again.",
        )
    
    # Delete OTP after successful verification
    await redis_client.delete(otp_key)
    
    # Get or create user profile
    user_profile = await profile_service.get_profile_by_email(request.email)
    if not user_profile:
        # Generate user_id from email or create UUID
        user_id = str(uuid.uuid4())
        user_profile = await profile_service.create_profile(
            email=request.email,
            user_id=user_id
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user_profile.user_id, "email": user_profile.email}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_profile.user_id,
        "email": user_profile.email,
    }

