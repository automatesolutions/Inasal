"""Background retry queue for BigQuery updates that fail due to streaming buffer"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.user_profile import PersonalityTraits

logger = logging.getLogger(__name__)


class BigQueryRetryQueue:
    """
    Manages retrying BigQuery updates that fail due to streaming buffer.
    Stores failed updates and retries them periodically with exponential backoff.
    """
    
    def __init__(self):
        self._retry_queue: Dict[str, Dict] = {}  # user_id -> {traits, last_attempt, attempt_count, next_retry}
        self._lock = asyncio.Lock()
        self._background_task = None
    
    async def add_retry(self, user_id: str, traits: PersonalityTraits):
        """Add a personality update to the retry queue"""
        async with self._lock:
            if user_id not in self._retry_queue:
                self._retry_queue[user_id] = {
                    "traits": traits,
                    "attempt_count": 0,
                    "first_attempt": datetime.utcnow(),
                    "last_attempt": None,
                    "next_retry": datetime.utcnow() + timedelta(minutes=2),  # First retry after 2 minutes
                    "status": "pending"
                }
                logger.info(f"📋 Added {user_id} to BigQuery retry queue (will retry in 2 minutes)")
            else:
                logger.warning(f"⚠️  {user_id} already in retry queue")
    
    async def should_retry(self, user_id: str) -> bool:
        """Check if a user should be retried now"""
        async with self._lock:
            if user_id not in self._retry_queue:
                return False
            
            item = self._retry_queue[user_id]
            if datetime.utcnow() >= item["next_retry"]:
                return True
        
        return False
    
    async def get_pending_retries(self) -> Dict[str, PersonalityTraits]:
        """Get all items that should be retried now"""
        async with self._lock:
            now = datetime.utcnow()
            pending = {}
            
            for user_id, item in list(self._retry_queue.items()):
                if item["status"] == "pending" and now >= item["next_retry"]:
                    pending[user_id] = item["traits"]
                    item["status"] = "retrying"
                    item["last_attempt"] = now
                    item["attempt_count"] += 1
            
            return pending
    
    async def mark_success(self, user_id: str):
        """Remove item from queue after successful update"""
        async with self._lock:
            if user_id in self._retry_queue:
                item = self._retry_queue[user_id]
                logger.info(f"✅ Removed {user_id} from retry queue after {item['attempt_count']} attempts")
                del self._retry_queue[user_id]
    
    async def mark_retry_failed(self, user_id: str):
        """Mark a retry attempt as failed, schedule next retry"""
        async with self._lock:
            if user_id in self._retry_queue:
                item = self._retry_queue[user_id]
                attempt = item["attempt_count"]
                
                # Exponential backoff: 2 min, 5 min, 10 min, 20 min, 30 min, 60 min
                backoff_minutes = min(2 ** attempt, 60)
                
                item["next_retry"] = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                item["status"] = "pending"
                
                logger.warning(f"⏳ {user_id} retry failed (attempt {attempt}), next retry in {backoff_minutes} minutes")
                
                # Give up after 6 hours or 12 attempts
                if attempt >= 12 or (datetime.utcnow() - item["first_attempt"]).total_seconds() > 21600:
                    logger.error(f"❌ Giving up on {user_id} after {attempt} attempts")
                    del self._retry_queue[user_id]
    
    def get_queue_status(self) -> Dict:
        """Get status of retry queue"""
        return {
            "total_pending": len(self._retry_queue),
            "items": {
                user_id: {
                    "attempt_count": item["attempt_count"],
                    "next_retry": item["next_retry"].isoformat() if item["next_retry"] else None,
                    "traits": item["traits"].model_dump()
                }
                for user_id, item in self._retry_queue.items()
            }
        }


# Global instance
retry_queue = BigQueryRetryQueue()


async def background_retry_task():
    """Background task that periodically retries failed BigQuery updates"""
    from app.user_profile import UserProfileService
    from app.bigquery_client import bigquery_client
    
    profile_service = UserProfileService()
    
    while True:
        try:
            # Wait before next check (check every 2 minutes)
            await asyncio.sleep(120)
            
            # Get items that should be retried
            pending_retries = await retry_queue.get_pending_retries()
            
            if not pending_retries:
                continue
            
            logger.info(f"🔄 Retrying BigQuery updates for {len(pending_retries)} users...")
            
            for user_id, traits in pending_retries.items():
                try:
                    logger.info(f"🔄 Retrying update for {user_id}...")
                    
                    update_data = {
                        "adventurous": traits.adventurous,
                        "cultural": traits.cultural,
                        "foodie": traits.foodie,
                        "nature_lover": traits.nature_lover,
                        "history_buff": traits.history_buff,
                        "social": traits.social,
                    }
                    
                    success = await bigquery_client.update_user_profile(user_id, update_data)
                    
                    if success:
                        await retry_queue.mark_success(user_id)
                        logger.info(f"✅ Successfully retried update for {user_id}")
                    else:
                        await retry_queue.mark_retry_failed(user_id)
                        logger.warning(f"⚠️  Retry failed for {user_id}, will try again later")
                
                except Exception as e:
                    logger.error(f"❌ Error retrying update for {user_id}: {e}")
                    await retry_queue.mark_retry_failed(user_id)
        
        except Exception as e:
            logger.error(f"❌ Error in background retry task: {e}", exc_info=True)
            # Continue running despite errors
            await asyncio.sleep(10)


def start_background_retry_task():
    """Start the background retry task"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    task = loop.create_task(background_retry_task())
    logger.info("🚀 Started background BigQuery retry task")
    return task
