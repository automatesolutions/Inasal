"""Unit tests for authentication functionality"""

import pytest
from app.auth import generate_otp, create_access_token, decode_access_token


class TestOTPGeneration:
    """Tests for OTP generation"""
    
    def test_otp_is_six_digits(self):
        """OTP should be exactly 6 digits"""
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_otp_is_random(self):
        """OTPs should be different (very unlikely to collide)"""
        otp1 = generate_otp()
        otp2 = generate_otp()
        # While technically possible, OTPs should be different
        assert otp1 != otp2


class TestJWTTokens:
    """Tests for JWT token creation and validation"""
    
    def test_create_token(self):
        """Should create a valid JWT token"""
        data = {"sub": "test-user-123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Should decode a valid token correctly"""
        data = {"sub": "test-user-456", "email": "test@example.com"}
        token = create_access_token(data)
        
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test-user-456"
        assert decoded["email"] == "test@example.com"
    
    def test_token_contains_expiry(self):
        """Token should contain expiration claim"""
        data = {"sub": "test-user", "email": "test@example.com"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        
        assert "exp" in decoded
