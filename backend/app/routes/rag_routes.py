"""RAG and real-time data API routes"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

# Conditionally import RAG engine
try:
    from app.rag_engine import RAGEngine
    rag_engine = RAGEngine()
    HAS_RAG = True
except ImportError:
    rag_engine = None
    HAS_RAG = False

router = APIRouter(prefix="/api/rag", tags=["rag"])


class WeatherResponse(BaseModel):
    """Weather response model"""
    weather: dict


class EventsResponse(BaseModel):
    """Events response model"""
    events: List[dict]
    count: int


class NewsResponse(BaseModel):
    """News response model"""
    news: List[dict]
    count: int


class LocalTipsRequest(BaseModel):
    """Request model for local tips"""
    query: str
    context: Optional[dict] = None


class LocalTipsResponse(BaseModel):
    """Response model for local tips"""
    tip: str


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    location: str = Query(default="Bacolod, Philippines"),
    use_cache: bool = Query(default=True),
):
    """Get current weather information"""
    if not HAS_RAG or not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. LangChain dependencies are not installed.",
        )
    weather = await rag_engine.get_weather_info(location, use_cache=use_cache)
    return WeatherResponse(weather=weather)


@router.get("/events", response_model=EventsResponse)
async def get_events(
    date: Optional[str] = Query(default=None),
    use_cache: bool = Query(default=True),
):
    """Get local events"""
    if not HAS_RAG or not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. LangChain dependencies are not installed.",
        )
    events = await rag_engine.get_local_events(date, use_cache=use_cache)
    return EventsResponse(events=events, count=len(events))


@router.get("/news", response_model=NewsResponse)
async def get_news(
    limit: int = Query(default=5, ge=1, le=20),
    use_cache: bool = Query(default=True),
):
    """Get local news"""
    if not HAS_RAG or not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. LangChain dependencies are not installed.",
        )
    news = await rag_engine.get_local_news(limit, use_cache=use_cache)
    return NewsResponse(news=news, count=len(news))


@router.post("/local-tips", response_model=LocalTipsResponse)
async def get_local_tips(request: LocalTipsRequest):
    """Get AI-generated local tips with RAG"""
    if not HAS_RAG or not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. LangChain dependencies are not installed.",
        )
    tip = await rag_engine.get_local_tips(request.query, request.context)
    return LocalTipsResponse(tip=tip)

