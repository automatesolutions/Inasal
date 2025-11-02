"""Authentication module - OAuth/email login, JWT token management"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return {"user_id": user_id, "email": payload.get("email")}


async def send_otp_email(email: str, otp: str) -> bool:
    """Send OTP email"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # If SMTP is not configured, print to console (for development)
    if not settings.smtp_user or not settings.smtp_password:
        print(f"\n{'='*60}")
        print(f"[DEV MODE] OTP Email would be sent to: {email}")
        print(f"[DEV MODE] Verification Code: {otp}")
        print(f"[DEV MODE] To enable real email sending, configure SMTP settings in .env")
        print(f"{'='*60}\n")
        return True
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Your Bacolod Tourist Verification Code"
        msg['From'] = settings.smtp_user
        msg['To'] = email
        
        # Create HTML email body
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #d97706;">Welcome to Bacolod Tourist! 🎭</h2>
              <p>Your verification code is:</p>
              <div style="background-color: #fef3c7; border: 2px solid #d97706; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                <h1 style="color: #d97706; font-size: 32px; letter-spacing: 5px; margin: 0;">{otp}</h1>
              </div>
              <p>This code will expire in 10 minutes.</p>
              <p style="color: #666; font-size: 12px; margin-top: 30px;">
                If you didn't request this code, please ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Welcome to Bacolod Tourist!
        
        Your verification code is: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        """
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email to {email}: {e}")
        # In development, still print OTP so testing can continue
        print(f"[DEV FALLBACK] OTP for {email}: {otp}")
        return True  # Return True to not break the flow during development


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    import random

    return str(random.randint(100000, 999999))

