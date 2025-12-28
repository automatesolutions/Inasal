"""RAG engine - RAG pipeline to fetch real-time data (weather, events, local tips)"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx

from langchain.prompts import ChatPromptTemplate

from app.config import settings
from app.llm_factory import get_chat_llm
from app.redis_client import redis_client

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class RAGEngine:
    """Retrieval-Augmented Generation engine for real-time data enrichment"""

    def __init__(self):
        # Use LLM factory (supports Ollama, OpenAI, Groq)
        self.llm = get_chat_llm(
            temperature=0.5,
            model=settings.openai_model if settings.llm_provider == "openai" else None
        )
        self.weather_cache_key = "weather:bacolod"
        self.events_cache_key = "events:bacolod"
        self.news_cache_key = "news:bacolod"

    async def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get cached data from Redis"""
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Error retrieving cache for {cache_key}: {e}")
        return None

    async def _set_cached_data(
        self, cache_key: str, data: Dict, ttl: int
    ) -> bool:
        """Store data in Redis cache"""
        try:
            await redis_client.set(cache_key, json.dumps(data), expire=ttl)
            return True
        except Exception as e:
            logger.warning(f"Error setting cache for {cache_key}: {e}")
        return False

    async def get_weather_info(
        self, location: str = "Bacolod, Philippines", use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get weather information with caching"""
        # Check cache first
        if use_cache:
            cached = await self._get_cached_data(self.weather_cache_key)
            if cached:
                logger.info(f"Weather data retrieved from cache for {location}")
                return cached

        weather_data = await self._fetch_weather_data(location)

        # Cache the result
        if weather_data and use_cache:
            await self._set_cached_data(
                self.weather_cache_key, weather_data, settings.weather_cache_ttl
            )

        return weather_data

    async def _fetch_weather_data(self, location: str) -> Dict[str, Any]:
        """Fetch weather data from API or return mock data"""
        if settings.enable_weather_api and settings.weather_api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    url = "https://api.openweathermap.org/data/2.5/weather"
                    params = {
                        "q": location,
                        "appid": settings.weather_api_key,
                        "units": "metric",
                    }
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    weather_info = {
                        "location": location,
                        "temperature": round(data["main"]["temp"], 1),
                        "feels_like": round(data["main"]["feels_like"], 1),
                        "condition": data["weather"][0]["description"].title(),
                        "humidity": data["main"]["humidity"],
                        "wind_speed": data.get("wind", {}).get("speed", 0),
                        "icon": data["weather"][0]["icon"],
                        "updated_at": datetime.utcnow().isoformat(),
                        "source": "openweathermap",
                    }
                    logger.info(f"Weather data fetched from API for {location}")
                    return weather_info
            except Exception as e:
                logger.error(f"Error fetching weather from API: {e}")
                # Fall through to mock data

        # Fallback to mock data
        logger.info(f"Using mock weather data for {location}")
        return {
            "location": location,
            "temperature": 28,
            "feels_like": 30,
            "condition": "Partly Cloudy",
            "humidity": 75,
            "wind_speed": 5.2,
            "icon": "02d",
            "updated_at": datetime.utcnow().isoformat(),
            "source": "mock",
        }

    async def get_local_events(
        self, date: Optional[str] = None, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get local events with caching"""
        cache_key = f"{self.events_cache_key}:{date or 'current'}"

        # Check cache first
        if use_cache:
            cached = await self._get_cached_data(cache_key)
            if cached:
                logger.info("Events data retrieved from cache")
                return cached.get("events", [])

        events = await self._fetch_local_events(date)

        # Cache the result
        if events and use_cache:
            await self._set_cached_data(
                cache_key, {"events": events}, settings.events_cache_ttl
            )

        return events

    async def _fetch_local_events(
        self, date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch local events from API or return mock data"""
        # TODO: Integrate with actual events API or RSS feed
        # For now, return mock data with some realistic events
        logger.info("Using mock events data")

        base_events = [
            {
                "id": "1",
                "title": "Masskara Festival",
                "date": "2025-10-19",
                "end_date": "2025-10-27",
                "location": "Bacolod City",
                "description": "Annual festival celebration with street dancing, food fairs, and cultural performances",
                "type": "festival",
                "source": "mock",
            },
            {
                "id": "2",
                "title": "Bacolod Food & Wine Festival",
                "date": "2025-03-15",
                "end_date": "2025-03-17",
                "location": "Bacolod City",
                "description": "Celebrate local cuisine and wines",
                "type": "food",
                "source": "mock",
            },
        ]

        # Filter by date if provided
        if date:
            filtered = [e for e in base_events if e["date"] <= date <= e.get("end_date", e["date"])]
            return filtered

        return base_events

    async def get_local_news(self, limit: int = 5, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get local news with caching"""
        # Check cache first
        if use_cache:
            cached = await self._get_cached_data(self.news_cache_key)
            if cached:
                logger.info("News data retrieved from cache")
                return cached.get("news", [])[:limit]

        news = await self._fetch_local_news()

        # Cache the result
        if news and use_cache:
            await self._set_cached_data(
                self.news_cache_key, {"news": news}, settings.news_cache_ttl
            )

        return news[:limit]

    async def _fetch_local_news(self) -> List[Dict[str, Any]]:
        """Fetch local news from RSS or API"""
        # TODO: Integrate with actual news RSS feed or API
        logger.info("Using mock news data")
        return [
            {
                "id": "1",
                "title": "Bacolod Tourism Reaches New Heights",
                "summary": "Tourist arrivals in Bacolod increased by 30% this year",
                "published_at": datetime.utcnow().isoformat(),
                "source": "mock",
            }
        ]

    async def get_local_tips(
        self, query: str, context: Optional[Dict] = None
    ) -> str:
        """Get local tips using RAG with real-time context"""
        if not self.llm:
            return "Local tips unavailable - API key not configured."

        # Gather real-time context
        context_data = {
            "query": query,
        }

        # Add weather context if relevant
        if any(keyword in query.lower() for keyword in ["weather", "clothing", "bring", "pack"]):
            weather = await self.get_weather_info()
            context_data["weather"] = weather

        # Add events context if relevant
        if any(keyword in query.lower() for keyword in ["event", "festival", "happening", "when"]):
            events = await self.get_local_events()
            if events:
                context_data["events"] = events[:3]  # Top 3 events

        # Add provided context
        if context:
            context_data.update(context)

        # Build RAG prompt
        system_prompt = """You are a friendly local guide from Bacolod, Philippines. 
Provide helpful, authentic tips about Bacolod using real-time information when available.
Be warm, welcoming, and practical. If you have real-time data (weather, events), use it to enhance your tips."""

        # Format context for prompt
        context_text = f"User Question: {query}\n\n"
        if "weather" in context_data:
            w = context_data["weather"]
            context_text += f"Current Weather: {w['temperature']}°C, {w['condition']}, Humidity: {w['humidity']}%\n"
        if "events" in context_data:
            context_text += "Upcoming Events:\n"
            for event in context_data["events"]:
                context_text += f"- {event['title']} on {event['date']}: {event['description']}\n"
        if context:
            context_text += f"\nAdditional Context: {json.dumps(context, indent=2)}\n"

        user_prompt = f"{context_text}\n\nProvide a helpful tip or answer based on this information:"

        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ]
            )

            chain = prompt | self.llm
            response = await chain.ainvoke({})
            logger.info(f"Generated local tip for query: {query[:50]}")
            return response.content
        except Exception as e:
            logger.error(f"Error generating local tip: {e}")
            return "I apologize, but I'm having trouble generating tips right now. Please try again later."

    async def enrich_recommendations_with_context(
        self, recommendations: List[Dict], user_profile: Optional[Dict] = None
    ) -> List[Dict]:
        """Enrich recommendations with real-time context (weather, events, scraped data)"""
        # Get real-time data
        weather = await self.get_weather_info()
        events = await self.get_local_events()
        
        # Get scraped travel data (hotels, adventures)
        scraped_data = None
        try:
            from app.scrapers.travel_scraper import travel_scraper
            scraped_data = await travel_scraper.scrape_all()
        except Exception as e:
            logger.debug(f"Could not load scraped data: {e}")

        # Enrich each recommendation
        enriched = []
        for rec in recommendations:
            enriched_rec = rec.copy()

            # Add weather context
            enriched_rec["weather_context"] = {
                "current_temp": weather["temperature"],
                "condition": weather["condition"],
                "recommendation": self._get_weather_recommendation(
                    rec, weather
                ),
            }

            # Check if any events match this recommendation
            matching_events = [
                e for e in events if self._events_match_recommendation(rec, e)
            ]
            if matching_events:
                enriched_rec["upcoming_events"] = matching_events

            # Add scraped data (hotels, adventures) if available
            if scraped_data:
                # Add nearby hotels if available
                if scraped_data.get("hotels"):
                    enriched_rec["nearby_hotels"] = scraped_data["hotels"][:3]  # Top 3
                
                # Add related adventures if available
                if scraped_data.get("adventures"):
                    # Match adventures by type/location
                    related_adventures = [
                        adv for adv in scraped_data["adventures"]
                        if any(tag in rec.get("tags", []) for tag in adv.get("tags", []))
                    ]
                    if related_adventures:
                        enriched_rec["related_adventures"] = related_adventures[:2]  # Top 2

            enriched.append(enriched_rec)

        return enriched

    def _get_weather_recommendation(
        self, recommendation: Dict, weather: Dict
    ) -> str:
        """Generate weather-based recommendation"""
        temp = weather["temperature"]
        condition = weather["condition"].lower()

        if "outdoor" in recommendation.get("type", "").lower() or any(
            tag in ["nature", "adventure"] for tag in recommendation.get("tags", [])
        ):
            if temp > 32:
                return "Hot day - bring sun protection and stay hydrated!"
            elif temp < 20:
                return "Cool weather - a light jacket would be comfortable."
            elif "rain" in condition:
                return "Rainy conditions - consider indoor alternatives or bring an umbrella."

        return f"Current weather: {temp}°C, {weather['condition']} - generally good conditions."

    def _events_match_recommendation(
        self, recommendation: Dict, event: Dict
    ) -> bool:
        """Check if an event matches a recommendation"""
        rec_name = recommendation.get("name", "").lower()
        rec_tags = [t.lower() for t in recommendation.get("tags", [])]

        event_title = event.get("title", "").lower()
        event_type = event.get("type", "").lower()

        # Simple matching logic
        if event_type in rec_tags:
            return True
        if any(tag in event_title for tag in rec_tags):
            return True
        if "festival" in event_type and "cultural" in rec_tags:
            return True

        return False
