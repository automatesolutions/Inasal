"""InstantDB client for real-time user profiles and personality data"""

import logging
import os
import json
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
            # Note: If InstantDB schema requires email, use phone-based placeholder
            # (InstantDB may require email even though we don't use it for auth)
            phone = profile_data.get("phone_number", "")
            placeholder_email = f"{phone}@phone.local" if phone else f"{user_id}@user.local"
            
            user_profile = {
                "id": user_id,
                "email": placeholder_email,  # Placeholder for schema requirement (not used for auth)
                "phone_number": phone,
                "first_name": profile_data.get("first_name"),
                "last_name": profile_data.get("last_name"),
                "name": profile_data.get("name"),
                "adventurous": profile_data.get("personality", {}).get("adventurous", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "cultural": profile_data.get("personality", {}).get("cultural", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "foodie": profile_data.get("personality", {}).get("foodie", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "nature_lover": profile_data.get("personality", {}).get("nature_lover", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "history_buff": profile_data.get("personality", {}).get("history_buff", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "social": profile_data.get("personality", {}).get("social", 0.5) if isinstance(profile_data.get("personality"), dict) else 0.5,
                "characteristics_summary": profile_data.get("characteristics_summary"),
                "source_links": profile_data.get("source_links", []),
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
            
            logger.debug(f"Creating profile in InstantDB with payload: {json.dumps(payload, indent=2)}")
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    logger.info(f"✅ User profile created in InstantDB: {user_id}")
                    logger.debug(f"   Response: {json.dumps(response_data, indent=2)[:500]}")
                except:
                    logger.info(f"✅ User profile created in InstantDB: {user_id} (response: {response.text[:200]})")
                
                # Wait a moment for data to be available for queries
                import asyncio
                await asyncio.sleep(1.0)  # Increased wait time
                
                # Verify the profile was actually created by querying it
                verify_profile = await self.get_user_profile(user_id)
                if verify_profile:
                    logger.info(f"✅ Profile verified immediately after creation: {user_id}")
                else:
                    logger.warning(f"⚠️  Profile created but not immediately queryable: {user_id} (may need more time)")
                
                return True
            else:
                logger.error(f"❌ InstantDB write error: {response.status_code} - {response.text[:500]}")
                logger.debug(f"   Payload sent: {json.dumps(payload, indent=2)}")
                try:
                    error_data = response.json()
                    logger.error(f"   Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating user profile in InstantDB: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from InstantDB"""
        if not self._is_available():
            return None
        
        try:
            # Clean user_id - remove any double dashes or formatting issues
            clean_user_id = user_id.strip().replace("--", "-")
            if clean_user_id != user_id:
                logger.warning(f"⚠️  Cleaned user_id: '{user_id}' -> '{clean_user_id}'")
            
            headers = self._get_headers()
            url = f"{self.base_url}/admin/query"
            
            # Use InstaQL syntax to query
            payload = {
                "query": {
                    "user_profiles": {
                        "$": {
                            "where": {
                                "id": clean_user_id
                            }
                        }
                    }
                }
            }
            
            logger.debug(f"Querying InstantDB for user_id: {clean_user_id}")
            logger.debug(f"   Query payload: {json.dumps(payload, indent=2)}")
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"   Query response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                
                # InstaQL returns results in data["user_profiles"] as an array
                if "user_profiles" in data and len(data["user_profiles"]) > 0:
                    profile = data["user_profiles"][0]
                    logger.warning(f"✅ Retrieved user profile from InstantDB: {clean_user_id}")
                    logger.warning(f"   Profile keys: {list(profile.keys()) if isinstance(profile, dict) else 'not a dict'}")
                    
                    # Log personality fields specifically
                    if isinstance(profile, dict):
                        personality_fields = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
                        personality_values = {k: profile.get(k, "NOT_FOUND") for k in personality_fields}
                        logger.warning(f"   🔍 Personality fields from InstantDB: {personality_values}")
                        # Check if all are defaults or missing
                        all_defaults_or_missing = all(
                            v == 0.5 or v == "NOT_FOUND" or v is None 
                            for v in personality_values.values()
                        )
                        if all_defaults_or_missing:
                            logger.error(f"   ❌ ALL PERSONALITY FIELDS ARE DEFAULTS OR MISSING IN INSTANTDB!")
                            logger.error(f"   This means personality analysis either didn't run or didn't save correctly")
                    
                    # Ensure 'id' field exists and map to 'user_id' if needed
                    if isinstance(profile, dict):
                        if "id" in profile and "user_id" not in profile:
                            profile["user_id"] = profile["id"]
                        elif "user_id" not in profile:
                            profile["user_id"] = clean_user_id
                    return profile
                else:
                    # Log when query succeeds but no results found (use DEBUG during retries, WARNING only if persistent)
                    # This is expected during profile creation verification retries
                    logger.debug(f"Query succeeded but no profile found for user_id: {clean_user_id} (this is normal during creation)")
                    logger.debug(f"   Response data: {json.dumps(data, indent=2)[:1000] if isinstance(data, dict) else str(data)[:500]}")
                    if isinstance(data, dict) and "user_profiles" in data:
                        logger.debug(f"   user_profiles array length: {len(data['user_profiles'])}")
                        if len(data['user_profiles']) > 0:
                            logger.debug(f"   First profile in array: {json.dumps(data['user_profiles'][0], indent=2)[:500]}")
                    # Try querying with original user_id in case there's a mismatch
                    if clean_user_id != user_id:
                        logger.debug(f"   Retrying with original user_id: {user_id}")
                        return await self.get_user_profile(user_id)
            
            else:
                logger.warning(f"⚠️  InstantDB query returned status {response.status_code}: {response.text[:200]}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile from InstantDB: {e}")
            import traceback
            logger.debug(f"   Traceback: {traceback.format_exc()}")
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
            
            # Merge updates with current data (exclude email - not stored in InstantDB)
            updated_profile = {**current_profile, **update_data}
            updated_profile.pop("email", None)  # Remove email if present
            updated_profile["updated_at"] = datetime.utcnow().isoformat()
            
            # Extract personality traits if present (handle both nested and flat formats)
            personality_fields = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
            
            # Case 1: Personality traits passed individually in update_data (from update_personality)
            for trait in personality_fields:
                if trait in update_data:
                    updated_profile[trait] = update_data[trait]
                    logger.debug(f"   Set {trait} = {update_data[trait]} (from flat update_data)")
            
            # Case 2: Personality traits nested under "personality" key
            if "personality" in update_data and isinstance(update_data["personality"], dict):
                for trait in personality_fields:
                    if trait in update_data["personality"]:
                        updated_profile[trait] = update_data["personality"][trait]
                        logger.debug(f"   Set {trait} = {update_data['personality'][trait]} (from nested personality dict)")
            
            # Log final personality values being saved
            final_personality = {trait: updated_profile.get(trait, "NOT_SET") for trait in personality_fields}
            logger.info(f"💾 Saving personality to InstantDB for {user_id}: {final_personality}")
            
            # Handle characteristics_summary and source_links if present
            if "characteristics_summary" in update_data:
                updated_profile["characteristics_summary"] = update_data["characteristics_summary"]
            if "source_links" in update_data:
                # Ensure source_links is a list
                links = update_data["source_links"]
                if isinstance(links, list):
                    updated_profile["source_links"] = links
                elif links is not None:
                    updated_profile["source_links"] = [links] if isinstance(links, str) else []
            
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
