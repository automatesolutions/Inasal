"""Unit tests for user profile models and logic"""

import pytest
from app.user_profile import (
    UserProfile,
    PersonalityTraits,
    UserPreferences
)


class TestPersonalityTraits:
    """Tests for PersonalityTraits model"""
    
    def test_default_traits(self):
        """Default traits should all be 0.5"""
        traits = PersonalityTraits()
        assert traits.adventurous == 0.5
        assert traits.cultural == 0.5
        assert traits.foodie == 0.5
        assert traits.nature_lover == 0.5
        assert traits.history_buff == 0.5
        assert traits.social == 0.5
    
    def test_custom_traits(self):
        """Should accept custom trait values"""
        traits = PersonalityTraits(
            adventurous=0.8,
            cultural=0.9,
            foodie=0.7
        )
        assert traits.adventurous == 0.8
        assert traits.cultural == 0.9
        assert traits.foodie == 0.7
    
    def test_trait_boundaries(self):
        """Traits should be bounded between 0 and 1"""
        traits = PersonalityTraits(adventurous=1.0, cultural=0.0)
        assert traits.adventurous == 1.0
        assert traits.cultural == 0.0


class TestUserPreferences:
    """Tests for UserPreferences model"""
    
    def test_default_preferences(self):
        """Default preferences should be None or empty"""
        prefs = UserPreferences()
        assert prefs.budget_range is None
        assert prefs.travel_style is None
        assert prefs.interests == []
        assert prefs.accessibility_needs == []
    
    def test_custom_preferences(self):
        """Should accept custom preferences"""
        prefs = UserPreferences(
            budget_range="mid-range",
            travel_style="solo",
            interests=["food", "culture", "nature"],
            accessibility_needs=["wheelchair"]
        )
        assert prefs.budget_range == "mid-range"
        assert prefs.travel_style == "solo"
        assert len(prefs.interests) == 3
        assert "food" in prefs.interests
        assert "wheelchair" in prefs.accessibility_needs


class TestUserProfile:
    """Tests for UserProfile model"""
    
    def test_create_profile(self):
        """Should create a profile with required fields"""
        profile = UserProfile(
            user_id="test-123",
            email="test@example.com",
            name="Test User"
        )
        
        assert profile.user_id == "test-123"
        assert profile.email == "test@example.com"
        assert profile.name == "Test User"
        assert isinstance(profile.personality, PersonalityTraits)
        assert isinstance(profile.preferences, UserPreferences)
    
    def test_profile_with_custom_traits(self):
        """Should accept custom personality traits"""
        traits = PersonalityTraits(adventurous=0.9, foodie=0.8)
        prefs = UserPreferences(budget_range="luxury")
        
        profile = UserProfile(
            user_id="test-456",
            email="test2@example.com",
            personality=traits,
            preferences=prefs
        )
        
        assert profile.personality.adventurous == 0.9
        assert profile.personality.foodie == 0.8
        assert profile.preferences.budget_range == "luxury"
