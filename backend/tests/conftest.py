"""Pytest configuration and fixtures"""

import pytest
from app.user_profile import UserProfile, PersonalityTraits, UserPreferences


@pytest.fixture
def sample_personality():
    """Sample personality traits for testing"""
    return PersonalityTraits(
        adventurous=0.7,
        cultural=0.8,
        foodie=0.9,
        nature_lover=0.6,
        history_buff=0.5,
        social=0.8
    )


@pytest.fixture
def sample_preferences():
    """Sample user preferences for testing"""
    return UserPreferences(
        budget_range="mid-range",
        travel_style="couple",
        interests=["food", "culture", "history"],
        accessibility_needs=[]
    )


@pytest.fixture
def sample_profile(sample_personality, sample_preferences):
    """Sample user profile for testing"""
    return UserProfile(
        user_id="test-user-123",
        email="test@example.com",
        name="Test User",
        personality=sample_personality,
        preferences=sample_preferences
    )
