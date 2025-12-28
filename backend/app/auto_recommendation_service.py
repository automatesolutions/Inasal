"""Auto-recommendation service for pre-generating recommendations on login"""

import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from app.user_profile import UserProfile
from app.recommendation import recommendation_engine
from app.rag_engine import RAGEngine
from app.redis_client import redis_client

# Conditionally import recommendation engine
try:
    from app.recommendation import recommendation_engine
    from app.rag_engine import RAGEngine
    HAS_RECOMMENDATIONS = True
except ImportError:
    HAS_RECOMMENDATIONS = False
    recommendation_engine = None
    RAGEngine = None


class AutoRecommendationService:
    """Service for automatically generating and caching recommendations"""

    CACHE_TTL = 3600  # 1 hour cache
    CACHE_KEY_PREFIX = "recommendations:"

    async def generate_onboarding_recommendations(
        self, user_id: str, profile: UserProfile
    ) -> Dict:
        """Generate recommendations automatically when user first logs in"""
        if not HAS_RECOMMENDATIONS or not recommendation_engine:
            return {}

        try:
            # Ensure recommendation engine is initialized
            if not recommendation_engine.vector_store:
                await recommendation_engine.initialize()

            # Generate recommendations for each section
            recommendations = await recommendation_engine.get_recommendations(
                profile, limit=6
            )

            hidden_gems = await recommendation_engine.get_hidden_gems(profile, limit=5)

            # Enrich with RAG
            rag_engine = RAGEngine()
            if rag_engine:
                recommendations = await rag_engine.enrich_recommendations_with_context(
                    recommendations
                )
                hidden_gems = await rag_engine.enrich_recommendations_with_context(
                    hidden_gems
                )

            # Filter cultural attractions
            cultural = [
                rec
                for rec in recommendations
                if rec.get("type") == "cultural" or "cultural" in rec.get("tags", [])
            ][:6]

            # Cache results
            cache_data = {
                "recommendations": recommendations,
                "hidden_gems": hidden_gems,
                "cultural": cultural,
                "generated_at": datetime.utcnow().isoformat(),
            }

            await self._cache_recommendations(user_id, cache_data)

            return cache_data

        except Exception as e:
            print(f"Error generating auto-recommendations: {e}")
            return {}

    async def get_cached_recommendations(self, user_id: str) -> Optional[Dict]:
        """Retrieve pre-generated recommendations from cache"""
        try:
            cache_key = f"{self.CACHE_KEY_PREFIX}{user_id}"
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            print(f"Error retrieving cached recommendations: {e}")
            return None

    async def _cache_recommendations(self, user_id: str, data: Dict):
        """Cache recommendations in Redis"""
        try:
            cache_key = f"{self.CACHE_KEY_PREFIX}{user_id}"
            await redis_client.set(
                cache_key, json.dumps(data), expire=self.CACHE_TTL
            )
        except Exception as e:
            print(f"Error caching recommendations: {e}")

    async def invalidate_cache(self, user_id: str):
        """Invalidate cached recommendations for a user"""
        try:
            cache_key = f"{self.CACHE_KEY_PREFIX}{user_id}"
            await redis_client.delete(cache_key)
        except Exception as e:
            print(f"Error invalidating cache: {e}")


# Global instance
auto_recommendation_service = AutoRecommendationService()

