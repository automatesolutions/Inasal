"""Tests for recommendation engine"""

import pytest

# Conditionally import recommendation engine
try:
    from app.recommendation import RecommendationEngine
    HAS_RECOMMENDATIONS = True
except ImportError:
    HAS_RECOMMENDATIONS = False
    RecommendationEngine = None

from app.user_profile import UserProfile, PersonalityTraits, UserPreferences

pytestmark = pytest.mark.skipif(not HAS_RECOMMENDATIONS, reason="LangChain dependencies not available")


@pytest.mark.asyncio
async def test_recommendation_engine_initialization():
    """Test recommendation engine initialization"""
    engine = RecommendationEngine()
    # Should not raise error even without API key
    await engine.initialize()
    assert engine is not None


@pytest.mark.asyncio
async def test_calculate_personality_score():
    """Test personality score calculation"""
    engine = RecommendationEngine()
    
    attraction = {
        "id": "1",
        "name": "Test Attraction",
        "personality_match": {
            "history_buff": 0.9,
            "cultural": 0.8,
            "adventurous": 0.5,
        }
    }
    
    personality = PersonalityTraits(
        history_buff=0.9,
        cultural=0.7,
        adventurous=0.3,
        foodie=0.2,
        nature_lover=0.2,
        social=0.5,
    )
    
    score = engine._calculate_personality_score(attraction, personality)
    assert 0.0 <= score <= 1.0
    assert score > 0.7  # Should be high due to strong history_buff match


@pytest.mark.asyncio
async def test_rank_by_personality():
    """Test ranking attractions by personality"""
    engine = RecommendationEngine()
    
    attractions = [
        {"id": "1", "name": "Historical Site", "personality_match": {"history_buff": 0.9}},
        {"id": "2", "name": "Food Place", "personality_match": {"foodie": 0.9}},
    ]
    
    profile = UserProfile(
        user_id="test-123",
        email="test@example.com",
        personality=PersonalityTraits(history_buff=0.9, foodie=0.3),
    )
    
    ranked = engine._rank_by_personality(attractions, profile, limit=2)
    
    assert len(ranked) == 2
    assert "personality_match_score" in ranked[0]
    # Historical site should rank higher
    assert ranked[0]["personality_match_score"] >= ranked[1]["personality_match_score"]


@pytest.mark.asyncio
async def test_build_query_from_profile():
    """Test query building from user profile"""
    engine = RecommendationEngine()
    
    profile = UserProfile(
        user_id="test-123",
        email="test@example.com",
        personality=PersonalityTraits(foodie=0.9, history_buff=0.8),
        preferences=UserPreferences(interests=["museums", "architecture"]),
    )
    
    query = engine._build_query_from_profile(profile)
    
    assert isinstance(query, str)
    assert len(query) > 0
    # Should include interests
    assert "museums" in query.lower() or "architecture" in query.lower()


def test_get_mock_recommendations():
    """Test mock recommendations when vector store unavailable"""
    engine = RecommendationEngine()
    
    profile = UserProfile(
        user_id="test-123",
        email="test@example.com",
    )
    
    # This should work even without initialized vector store
    recommendations = engine._get_mock_recommendations(profile, limit=5)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5

