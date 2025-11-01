"""Tests for authentication module"""

import pytest
from app.auth import verify_password, get_password_hash, generate_otp


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

