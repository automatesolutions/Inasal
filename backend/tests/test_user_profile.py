"""Tests for user profile module"""

import pytest
from datetime import datetime
from app.user_profile import (
    UserProfileService,
    PersonalityTraits,
    UserPreferences,
    UserProfile,
)
from app.models.interaction_log import InteractionLogCreate


@pytest.mark.asyncio
async def test_create_profile():
    """Test creating a user profile"""
    service = UserProfileService()
    profile = await service.create_profile(
        email="test@example.com",
        user_id="test-user-123",
        name="Test User"
    )
    
    assert profile is not None
    assert profile.email == "test@example.com"
    assert profile.user_id == "test-user-123"
    assert profile.name == "Test User"
    assert profile.personality is not None
    assert profile.preferences is not None


@pytest.mark.asyncio
async def test_get_profile():
    """Test getting a user profile"""
    service = UserProfileService()
    
    # Create profile first
    created = await service.create_profile(
        email="get@example.com",
        user_id="get-user-123"
    )
    
    # Retrieve profile
    profile = await service.get_profile("get-user-123")
    
    assert profile is not None
    assert profile.user_id == "get-user-123"
    assert profile.email == "get@example.com"


@pytest.mark.asyncio
async def test_update_personality():
    """Test updating personality traits"""
    service = UserProfileService()
    
    # Create profile
    await service.create_profile(
        email="personality@example.com",
        user_id="personality-user-123"
    )
    
    # Update personality
    new_traits = PersonalityTraits(
        adventurous=0.9,
        cultural=0.7,
        foodie=0.8
    )
    
    updated = await service.update_personality("personality-user-123", new_traits)
    
    assert updated is not None
    assert updated.personality.adventurous == 0.9
    assert updated.personality.cultural == 0.7
    assert updated.personality.foodie == 0.8


@pytest.mark.asyncio
async def test_update_preferences():
    """Test updating user preferences"""
    service = UserProfileService()
    
    # Create profile
    await service.create_profile(
        email="prefs@example.com",
        user_id="prefs-user-123"
    )
    
    # Update preferences
    new_prefs = UserPreferences(
        budget_range="mid-range",
        travel_style="couple",
        interests=["food", "culture"],
        accessibility_needs=[]
    )
    
    updated = await service.update_preferences("prefs-user-123", new_prefs)
    
    assert updated is not None
    assert updated.preferences.budget_range == "mid-range"
    assert updated.preferences.travel_style == "couple"
    assert "food" in updated.preferences.interests
    assert "culture" in updated.preferences.interests


@pytest.mark.asyncio
async def test_log_interaction():
    """Test logging user interaction"""
    service = UserProfileService()
    
    log = InteractionLogCreate(
        user_id="log-user-123",
        interaction_type="search",
        content={"query": "restaurants", "results_count": 5},
        metadata={"device": "mobile"}
    )
    
    result = await service.log_interaction(log)
    assert result is True


@pytest.mark.asyncio
async def test_get_interaction_history():
    """Test retrieving interaction history"""
    service = UserProfileService()
    
    # Log some interactions
    await service.log_interaction(
        InteractionLogCreate(
            user_id="history-user-123",
            interaction_type="view",
            content={"destination": "The Ruins"}
        )
    )
    
    await service.log_interaction(
        InteractionLogCreate(
            user_id="history-user-123",
            interaction_type="like",
            content={"destination_id": "123"}
        )
    )
    
    # Get history
    history = await service.get_interaction_history("history-user-123", limit=10)
    
    assert len(history) >= 2
    assert history[0]["interaction_type"] in ["view", "like"]

