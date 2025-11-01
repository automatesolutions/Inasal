"""Redis client for caching and session management"""

import json
from typing import Optional, Any
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings


class RedisClient:
    """Redis client wrapper"""

    _client: Optional[Redis] = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self._client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            print("✅ Connected to Redis")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            print("✅ Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self._client:
            await self.connect()
        return await self._client.get(key)

    async def set(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration (seconds)"""
        if not self._client:
            await self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self._client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete key from Redis"""
        if not self._client:
            await self.connect()
        return await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            await self.connect()
        return await self._client.exists(key) > 0


redis_client = RedisClient()

