"""Authentication API routes"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.auth import send_otp_email, generate_otp, create_access_token
from app.user_profile import UserProfileService

router = APIRouter(prefix="/api/auth", tags=["auth"])
profile_service = UserProfileService()


class EmailRequest(BaseModel):
    email: EmailStr


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp: str


@router.post("/send-otp")
async def send_otp(request: EmailRequest):
    """Send OTP to user's email"""
    otp = generate_otp()
    # TODO: Store OTP in Redis with expiration
    await send_otp_email(request.email, otp)
    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    """Verify OTP and return JWT token"""
    # TODO: Verify OTP from Redis
    # For now, accept any OTP for development
    user_profile = await profile_service.get_profile(request.email)
    if not user_profile:
        user_profile = await profile_service.create_profile(
            request.email, user_id=request.email  # TODO: Generate proper user_id
        )

    access_token = create_access_token(
        data={"sub": user_profile.user_id, "email": user_profile.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}

