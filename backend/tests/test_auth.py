"""Tests for authentication module"""

import pytest
from datetime import timedelta
from app.auth import (
    verify_password,
    get_password_hash,
    generate_otp,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    """Test password hashing and verification"""
    password = "test_password_123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_otp_generation():
    """Test OTP generation"""
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_create_access_token():
    """Test JWT token creation"""
    data = {"sub": "test-user-123", "email": "test@example.com"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token():
    """Test JWT token decoding"""
    data = {"sub": "test-user-123", "email": "test@example.com"}
    token = create_access_token(data)
    
    decoded = decode_access_token(token)
    
    assert decoded is not None
    assert decoded["sub"] == "test-user-123"
    assert decoded["email"] == "test@example.com"


def test_decode_invalid_token():
    """Test decoding invalid token"""
    invalid_token = "invalid.token.here"
    decoded = decode_access_token(invalid_token)
    
    assert decoded is None

