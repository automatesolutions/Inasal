"""Redis client for caching and session management"""

import json
from typing import Optional, Any
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings


class RedisClient:
    """Redis client wrapper"""

    _client: Optional[Redis] = None
    _connection_failed: bool = False  # Track if connection has failed to avoid repeated warnings

    async def connect(self, silent: bool = False):
        """Connect to Redis - optional, won't fail if Redis unavailable"""
        # If we've already failed to connect, don't try again
        if self._connection_failed:
            return
        
        try:
            self._client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            if not silent:
                print("[SUCCESS] Connected to Redis")
            self._connection_failed = False  # Reset flag on success
        except Exception as e:
            self._connection_failed = True
            self._client = None
            if not silent:
                print(f"[WARNING] Redis not available: {e}")
                print("   Server will continue without Redis")
            # Don't raise - allow server to start without Redis

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            print("[SUCCESS] Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception:
            return None

    async def set(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration (seconds)"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return await self._client.set(key, value, ex=expire)
        except Exception:
            return False

    async def delete(self, key: str) -> int:
        """Delete key from Redis"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return 0
        try:
            return await self._client.delete(key)
        except Exception:
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception:
            return False

    async def incr(self, key: str) -> int:
        """Increment a key's value (atomic operation)"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return 0
        try:
            return await self._client.incr(key)
        except Exception:
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        if not self._client and not self._connection_failed:
            await self.connect(silent=True)
        if not self._client:
            return False
        try:
            return await self._client.expire(key, seconds)
        except Exception:
            return False

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._client is not None


redis_client = RedisClient()

