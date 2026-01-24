"""InstantDB client for real-time user profiles and personality data"""

import logging
import os
from typing import Optional, Dict, Any
import httpx
from datetime import datetime
from dotenv import load_dotenv
import uuid as uuid_lib

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class InstantDBClient:
    """Handle all InstantDB operations for user data using Admin HTTP API"""
    
    def __init__(self):
        self.app_id = os.getenv("INSTANTDB_APP_ID")
        self.admin_token = os.getenv("INSTANTDB_ADMIN_TOKEN")
        self.base_url = "https://api.instantdb.com"
        self.client = httpx.AsyncClient(timeout=30.0)
        self._initialized = False
        
        if self.app_id and self.admin_token:
            self._initialized = True
            logger.info(f"✅ InstantDB initialized with app_id: {self.app_id[:8]}...")
        else:
            logger.warning("⚠️  InstantDB credentials not found in .env")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for InstantDB API"""
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "App-Id": self.app_id,
            "Content-Type": "application/json"
        }
    
    def _is_available(self) -> bool:
        """Check if InstantDB is available"""
        return self._initialized and self.app_id and self.admin_token
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Create a new user profile in InstantDB"""
        if not self._is_available():
            logger.warning("⚠️  InstantDB not available")
            return False
        
        try:
            # Prepare user profile
            user_profile = {
                "id": user_id,
                "email": profile_data.get("email"),
                "phone_number": profile_data.get("phone_number"),
                "first_name": profile_data.get("first_name"),
                "last_name": profile_data.get("last_name"),
                "name": profile_data.get("name"),
                "adventurous": profile_data.get("personality", {}).get("adventurous", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "cultural": profile_data.get("personality", {}).get("cultural", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "foodie": profile_data.get("personality", {}).get("foodie", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "nature_lover": profile_data.get("personality", {}).get("nature_lover", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "history_buff": profile_data.get("personality", {}).get("history_buff", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "social": profile_data.get("personality", {}).get("social", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            # Use HTTP Admin API for transact (write)
            headers = self._get_headers()
            url = f"{self.base_url}/admin/transact"
            
            # Prepare transaction step: ["update", collection, id, data]
            payload = {
                "steps": [
                    ["update", "user_profiles", user_id, user_profile]
                ]
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ User profile created in InstantDB: {user_id}")
                return True
            else:
                logger.error(f"❌ InstantDB write error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating user profile in InstantDB: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from InstantDB"""
        if not self._is_available():
            return None
        
        try:
            headers = self._get_headers()
            url = f"{self.base_url}/admin/query"
            
            # Use InstaQL syntax to query
            payload = {
                "query": {
                    "user_profiles": {
                        "$": {
                            "where": {
                                "id": user_id
                            }
                        }
                    }
                }
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # InstaQL returns results in data["user_profiles"] as an array
                if "user_profiles" in data and len(data["user_profiles"]) > 0:
                    profile = data["user_profiles"][0]
                    logger.info(f"✅ Retrieved user profile from InstantDB: {user_id}")
                    return profile
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile from InstantDB: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user profile in InstantDB - INSTANT (no 90-minute lock!)"""
        if not self._is_available():
            return False
        
        try:
            # Get current profile first
            current_profile = await self.get_user_profile(user_id)
            if not current_profile:
                logger.warning(f"⚠️  User profile not found for update: {user_id}")
                return False
            
            # Merge updates with current data
            updated_profile = {**current_profile, **update_data}
            updated_profile["updated_at"] = datetime.utcnow().isoformat()
            
            # Extract personality traits if present
            if "personality" in update_data and isinstance(update_data["personality"], dict):
                for trait in ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]:
                    if trait in update_data["personality"]:
                        updated_profile[trait] = update_data["personality"][trait]
            
            headers = self._get_headers()
            url = f"{self.base_url}/admin/transact"
            
            # Prepare transaction step: ["update", collection, id, data]
            payload = {
                "steps": [
                    ["update", "user_profiles", user_id, updated_profile]
                ]
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ User profile updated in InstantDB (INSTANTLY!): {user_id}")
                logger.info(f"   Updated traits: {[k for k in update_data.keys() if k != 'personality']}")
                return True
            else:
                logger.error(f"❌ InstantDB update error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating user profile in InstantDB: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
instantdb_client = InstantDBClient()
