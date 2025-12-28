"""Make.com webhook client for AI workflows"""

import httpx
from typing import Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MakeClient:
    """Client for calling Make.com webhook workflows"""

    def __init__(self):
        self.chat_webhook = settings.make_webhook_chat
        self.recommendations_webhook = settings.make_webhook_recommendations
        self.persona_webhook = settings.make_webhook_persona
        self.client = httpx.AsyncClient(timeout=60.0)

    async def send_chat_message(
        self,
        user_id: str,
        message: str
    ) -> Optional[Dict[str, Any]]:
        """Send chat message to Make.com chat workflow"""
        if not self.chat_webhook:
            logger.warning("Make.com chat webhook not configured")
            return None

        try:
            response = await self.client.post(
                self.chat_webhook,
                json={
                    "user_id": user_id,
                    "message": message,
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Make.com chat webhook: {e}")
            return None

    async def get_recommendations(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Trigger recommendation generation via Make.com"""
        if not self.recommendations_webhook:
            logger.warning("Make.com recommendations webhook not configured")
            return None

        try:
            response = await self.client.post(
                self.recommendations_webhook,
                json={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Make.com recommendations webhook: {e}")
            return None

    async def trigger_persona_discovery(
        self,
        user_id: str,
        first_name: str,
        last_name: str
    ) -> Optional[Dict[str, Any]]:
        """Trigger persona discovery workflow via Make.com"""
        if not self.persona_webhook:
            logger.warning("Make.com persona webhook not configured")
            return None

        try:
            response = await self.client.post(
                self.persona_webhook,
                json={
                    "user_id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Make.com persona webhook: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
make_client = MakeClient()

