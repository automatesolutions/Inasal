"""Tests for RAG engine"""

import pytest
from datetime import datetime

# Conditionally import RAG engine
try:
    from app.rag_engine import RAGEngine
    HAS_RAG = True
except ImportError:
    HAS_RAG = False
    RAGEngine = None

pytestmark = pytest.mark.skipif(not HAS_RAG, reason="LangChain dependencies not available")


@pytest.mark.asyncio
async def test_get_weather_info():
    """Test weather information retrieval"""
    engine = RAGEngine()
    
    weather = await engine.get_weather_info()
    
    assert weather is not None
    assert "location" in weather
    assert "temperature" in weather
    assert "condition" in weather
    assert weather["location"] == "Bacolod, Philippines"


@pytest.mark.asyncio
async def test_weather_caching():
    """Test weather data caching"""
    engine = RAGEngine()
    
    # First call - should fetch or use mock
    weather1 = await engine.get_weather_info(use_cache=False)
    
    # Second call with cache - should return cached data
    weather2 = await engine.get_weather_info(use_cache=True)
    
    # Both should have same structure
    assert weather1.keys() == weather2.keys()


@pytest.mark.asyncio
async def test_get_local_events():
    """Test local events retrieval"""
    engine = RAGEngine()
    
    events = await engine.get_local_events()
    
    assert isinstance(events, list)
    if events:
        assert "title" in events[0]
        assert "date" in events[0]
        assert "location" in events[0]


@pytest.mark.asyncio
async def test_get_local_news():
    """Test local news retrieval"""
    engine = RAGEngine()
    
    news = await engine.get_local_news(limit=5)
    
    assert isinstance(news, list)
    assert len(news) <= 5
    if news:
        assert "title" in news[0]


@pytest.mark.asyncio
async def test_get_local_tips():
    """Test local tips generation"""
    engine = RAGEngine()
    
    # Mock LLM is not configured, so this will return a message
    tip = await engine.get_local_tips("What should I pack for Bacolod?")
    
    assert isinstance(tip, str)
    assert len(tip) > 0


@pytest.mark.asyncio
async def test_enrich_recommendations_with_context():
    """Test recommendation enrichment"""
    engine = RAGEngine()
    
    recommendations = [
        {
            "id": "1",
            "name": "The Ruins",
            "type": "historical",
            "tags": ["outdoor", "historical"],
        },
        {
            "id": "2",
            "name": "Masskara Festival",
            "type": "cultural",
            "tags": ["cultural", "festival"],
        },
    ]
    
    enriched = await engine.enrich_recommendations_with_context(recommendations)
    
    assert len(enriched) == len(recommendations)
    assert "weather_context" in enriched[0]
    assert "current_temp" in enriched[0]["weather_context"]


@pytest.mark.asyncio
async def test_weather_recommendation():
    """Test weather-based recommendations"""
    engine = RAGEngine()
    
    recommendation = {
        "name": "Mambukal Resort",
        "type": "nature",
        "tags": ["outdoor", "nature", "hiking"],
    }
    
    hot_weather = {"temperature": 35, "condition": "Sunny", "humidity": 80}
    rec = engine._get_weather_recommendation(recommendation, hot_weather)
    
    assert isinstance(rec, str)
    assert len(rec) > 0

