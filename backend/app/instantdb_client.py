"""InstantDB client for real-time user profiles and personality data"""

import logging
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
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
    
    # --- Curated resources (from Google Sheet: Bacolod Details) ---
    CURATED_COLLECTION = "curated_resources"
    
    async def save_curated_category(
        self, category_slug: str, urls: list, content_hash: Optional[str] = None
    ) -> bool:
        """Save or update one category of curated URLs (from Google Sheet)."""
        if not self._is_available():
            return False
        try:
            doc = {
                "id": category_slug,
                "urls": urls,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if content_hash:
                doc["content_hash"] = content_hash
            payload = {
                "steps": [
                    ["update", self.CURATED_COLLECTION, category_slug, doc]
                ]
            }
            response = await self.client.post(
                f"{self.base_url}/admin/transact",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Curated category saved: {category_slug} ({len(urls)} URLs)")
                return True
            logger.error(f"❌ InstantDB curated save error: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Error saving curated category: {e}")
            return False
    
    async def get_all_curated_resources(self) -> Dict[str, Any]:
        """Get all curated resources: { category_slug: { urls, updated_at, content_hash } }."""
        if not self._is_available():
            return {}
        try:
            payload = {
                "query": {
                    "curated_resources": {}
                }
            }
            response = await self.client.post(
                f"{self.base_url}/admin/query",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code != 200:
                return {}
            data = response.json()
            items = data.get("curated_resources") or []
            return {
                item["id"]: {
                    "urls": item.get("urls", []),
                    "updated_at": item.get("updated_at"),
                    "content_hash": item.get("content_hash"),
                }
                for item in items
                if item.get("id")
            }
        except Exception as e:
            logger.error(f"❌ Error getting curated resources: {e}")
            return {}
    
    async def get_curated_urls_for_category(self, category_slug: str) -> List[str]:
        """Get list of URLs for a category (e.g. accommodation_hotels, tourist_spots)."""
        all_ = await self.get_all_curated_resources()
        cat = all_.get(category_slug)
        return (cat.get("urls", []) or []) if cat else []
    
    # --- Scraped content (from Google Sheet URLs) ---
    # Use separate collections per category to create "workspaces" in InstantDB
    SCRAPED_CONTENT_COLLECTION_PREFIX = "scraped_content_"
    
    def _get_collection_for_category(self, category: str) -> str:
        """Get collection name for a category (creates separate workspace per category)"""
        if not category:
            return "scraped_content_unknown"
        # Map category slugs to collection names
        category_collections = {
            "accommodation_hotels": "scraped_content_accommodation_hotels",
            "tourist_spots": "scraped_content_tourist_spots",
            "restaurants_food": "scraped_content_restaurants_food",
            "dangerous_areas": "scraped_content_dangerous_areas",
            "scams": "scraped_content_scams",
            "secret_places": "scraped_content_secret_places",
        }
        collection_name = category_collections.get(category, f"scraped_content_{category}")
        return collection_name
    
    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure a collection exists in InstantDB by creating an empty placeholder"""
        if not self._is_available():
            return
        try:
            # Create a placeholder document to ensure collection exists
            placeholder_id = "00000000-0000-0000-0000-000000000000"
            placeholder_doc = {
                "id": placeholder_id,
                "_placeholder": True,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            payload = {
                "steps": [
                    ["update", collection_name, placeholder_id, placeholder_doc]
                ]
            }
            
            response = await self.client.post(
                f"{self.base_url}/admin/transact",
                json=payload,
                headers=self._get_headers(),
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"✅ Ensured collection '{collection_name}' exists")
                # Delete placeholder immediately
                delete_payload = {
                    "steps": [
                        ["delete", collection_name, placeholder_id]
                    ]
                }
                await self.client.post(
                    f"{self.base_url}/admin/transact",
                    json=delete_payload,
                    headers=self._get_headers(),
                )
            else:
                logger.debug(f"Collection '{collection_name}' may already exist (status: {response.status_code})")
        except Exception as e:
            logger.debug(f"Could not ensure collection exists (may already exist): {e}")
    
    async def save_scraped_content(self, url: str, content: Dict[str, Any]) -> bool:
        """
        Save scraped content from a URL to category-specific collection (workspace).
        Uses UUID-based ID derived from URL hash.
        Enhanced to handle location, events, and personality_keywords fields.
        """
        if not self._is_available():
            return False
        try:
            import hashlib
            category = content.get("category", "unknown")
            
            # Generate UUID-like ID from URL hash (InstantDB requires UUID format)
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            # Convert to UUID format: 8-4-4-4-12
            uuid_id = f"{url_hash[:8]}-{url_hash[8:12]}-{url_hash[12:16]}-{url_hash[16:20]}-{url_hash[20:32]}"
            
            # Get category-specific collection name (creates separate workspace)
            collection_name = self._get_collection_for_category(category)
            
            # Prepare document with all fields
            # Include entity-specific fields extracted by LLM
            doc = {
                "id": uuid_id,
                "url": url,
                "category": category,
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            # Add basic fields
            for key in ["title", "description", "content_text", "domain", "places_mentioned"]:
                if key in content:
                    doc[key] = content[key]
            
            # Add images (use entity-specific images if available, otherwise fallback to scraped images)
            if "images" in content and content["images"]:
                doc["images"] = content["images"]
            else:
                doc["images"] = []
            
            # Add location (entity-specific address takes priority)
            if "address" in content and content["address"]:
                # If entity has specific address, create location object
                location = content.get("location", {})
                if isinstance(location, dict):
                    location["address"] = content["address"]
                else:
                    location = {"address": content["address"]}
                doc["location"] = location
            elif "location" in content and content["location"]:
                doc["location"] = content["location"]
            
            # Add entity-specific fields based on category
            if category == "accommodation_hotels":
                for key in ["hotel_name", "phone", "email", "website", "amenities", 
                           "room_types", "price_range", "rating", "check_in_time", 
                           "check_out_time", "policies"]:
                    if key in content:
                        doc[key] = content[key]
                # Use hotel_name as title if available
                if "hotel_name" in content and content["hotel_name"]:
                    doc["title"] = content["hotel_name"]
                    doc["name"] = content["hotel_name"]  # Also add as 'name' field
            
            elif category == "restaurants_food":
                for key in ["restaurant_name", "phone", "email", "website", "cuisine_type",
                           "specialties", "price_range", "opening_hours", "rating", 
                           "features", "reservations"]:
                    if key in content:
                        doc[key] = content[key]
                # Use restaurant_name as title if available
                if "restaurant_name" in content and content["restaurant_name"]:
                    doc["title"] = content["restaurant_name"]
                    doc["name"] = content["restaurant_name"]
            
            elif category == "tourist_spots":
                for key in ["attraction_name", "opening_hours", "entrance_fee", 
                           "best_time_to_visit", "duration", "highlights", "activities",
                           "contact_info", "parking", "accessibility", "category"]:
                    if key in content:
                        doc[key] = content[key]
                # Use attraction_name as title if available
                if "attraction_name" in content and content["attraction_name"]:
                    doc["title"] = content["attraction_name"]
                    doc["name"] = content["attraction_name"]
            
            elif category == "secret_places":
                for key in ["place_name", "why_secret", "best_time_to_visit", "how_to_find",
                           "what_to_expect", "tips", "category"]:
                    if key in content:
                        doc[key] = content[key]
                # Use place_name as title if available
                if "place_name" in content and content["place_name"]:
                    doc["title"] = content["place_name"]
                    doc["name"] = content["place_name"]
            
            elif category == "secret_places":
                for key in ["place_name", "why_secret", "best_time_to_visit", 
                           "how_to_find", "what_to_expect", "tips"]:
                    if key in content:
                        doc[key] = content[key]
                # Use place_name as title if available
                if "place_name" in content and content["place_name"]:
                    doc["title"] = content["place_name"]
                    doc["name"] = content["place_name"]
            
            elif category == "dangerous_areas":
                for key in ["name", "location", "warning_signs", "how_to_avoid", 
                           "severity", "reported_incidents", "time_of_concern", "type_of_danger"]:
                    if key in content:
                        doc[key] = content[key]
                # Use name as title if available
                if "name" in content and content["name"]:
                    doc["title"] = content["name"]
            
            elif category == "scams":
                for key in ["name", "location", "warning_signs", "how_to_avoid", 
                           "severity", "reported_incidents", "scam_type", "target_victims", "common_tactics"]:
                    if key in content:
                        doc[key] = content[key]
                # Use name as title if available
                if "name" in content and content["name"]:
                    doc["title"] = content["name"]
            
            # Add common fields
            if "events" in content and content["events"]:
                doc["events"] = content["events"]
            
            if "personality_keywords" in content and content["personality_keywords"]:
                doc["personality_keywords"] = content["personality_keywords"]
            
            # Add any other fields that might be present
            for key in ["rating", "publish_date"]:
                if key in content and key not in doc:
                    doc[key] = content[key]
            
            payload = {
                "steps": [
                    ["update", collection_name, uuid_id, doc]
                ]
            }
            response = await self.client.post(
                f"{self.base_url}/admin/transact",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Scraped content saved to InstantDB collection '{collection_name}': {url[:60]}... (ID: {uuid_id})")
                try:
                    response_data = response.json()
                    logger.debug(f"   Response: {json.dumps(response_data, indent=2)[:500]}")
                except:
                    pass
                return True
            logger.error(f"❌ InstantDB scraped content save error: {response.status_code}")
            logger.error(f"   URL: {url[:80]}")
            logger.error(f"   Response: {response.text[:500]}")
            logger.error(f"   Payload keys: {list(payload.keys())}")
            logger.error(f"   Doc keys: {list(doc.keys())}")
            return False
        except Exception as e:
            logger.error(f"❌ Error saving scraped content: {e}")
            return False
    
    async def url_already_scraped(self, url: str, category: str) -> bool:
        """Check if a URL has already been scraped for this category."""
        if not self._is_available():
            return False
        try:
            collection_name = self._get_collection_for_category(category)
            payload = {
                "query": {
                    collection_name: {
                        "$": {
                            "where": {
                                "url": url
                            }
                        }
                    }
                }
            }
            response = await self.client.post(
                f"{self.base_url}/admin/query",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get(collection_name) or []
                return len(items) > 0
            return False
        except Exception as e:
            logger.debug(f"Error checking if URL already scraped: {e}")
            return False
    
    async def get_scraped_content_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all scraped content for a category from its category-specific collection."""
        if not self._is_available():
            logger.warning(f"InstantDB not available, cannot get scraped content for {category}")
            return []
        try:
            # Query category-specific collection
            collection_name = self._get_collection_for_category(category)
            payload = {
                "query": {
                    collection_name: {}
                }
            }
            logger.debug(f"Querying InstantDB collection '{collection_name}' for category '{category}'")
            
            response = await self.client.post(
                f"{self.base_url}/admin/query",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code != 200:
                logger.warning(f"Query failed with status {response.status_code}: {response.text[:500]}")
                return []
            
            data = response.json()
            logger.debug(f"Query response keys: {list(data.keys())}")
            items = data.get(collection_name) or []
            logger.info(f"Found {len(items)} items for category '{category}' in collection '{collection_name}'")
            
            # Log sample item if available
            if items:
                sample = items[0]
                logger.debug(f"Sample item for {category}: {json.dumps({k: v for k, v in sample.items() if k != 'content_text'}, indent=2)[:500]}")
            
            return items
        except Exception as e:
            logger.error(f"❌ Error getting scraped content for category '{category}': {e}", exc_info=True)
            return []
    
    async def get_all_scraped_content(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all scraped content grouped by category from all category-specific collections."""
        if not self._is_available():
            logger.warning("InstantDB not available, cannot get all scraped content")
            return {}
        try:
            # Query all category-specific collections
            category_collections = [
                "scraped_content_accommodation_hotels",
                "scraped_content_tourist_spots",
                "scraped_content_restaurants_food",
                "scraped_content_dangerous_areas",
                "scraped_content_scams",
                "scraped_content_secret_places",
            ]
            
            # Build query for all collections
            query_dict = {}
            for collection in category_collections:
                query_dict[collection] = {}
            
            payload = {"query": query_dict}
            logger.debug("Querying InstantDB for all scraped content from category collections")
            
            response = await self.client.post(
                f"{self.base_url}/admin/query",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code != 200:
                logger.warning(f"Query failed with status {response.status_code}: {response.text[:500]}")
                return {}
            
            data = response.json()
            logger.debug(f"Query response keys: {list(data.keys())}")
            
            # Group by category
            grouped = {}
            category_map = {
                "scraped_content_accommodation_hotels": "accommodation_hotels",
                "scraped_content_tourist_spots": "tourist_spots",
                "scraped_content_restaurants_food": "restaurants_food",
                "scraped_content_dangerous_areas": "dangerous_areas",
                "scraped_content_scams": "scams",
                "scraped_content_secret_places": "secret_places",
            }
            
            total_items = 0
            for collection_name, category_slug in category_map.items():
                items = data.get(collection_name) or []
                if items:
                    grouped[category_slug] = items
                    total_items += len(items)
                    logger.debug(f"Retrieved {len(items)} items from {collection_name}")
            
            logger.info(f"Retrieved {total_items} total scraped content items from {len(grouped)} category collections")
            logger.info(f"Categories with data: {list(grouped.keys())}")
            return grouped
        except Exception as e:
            logger.error(f"❌ Error getting all scraped content: {e}", exc_info=True)
            return {}
    
    async def get_scraped_content_by_location(
        self, latitude: float, longitude: float, radius_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Find scraped content near coordinates.
        Note: InstantDB doesn't support geo queries natively, so we fetch all and filter in memory.
        For production, consider using a geospatial database or external service.
        """
        if not self._is_available():
            return []
        try:
            # Get all scraped content with location data
            all_content = await self.get_all_scraped_content()
            results = []
            
            # Simple distance calculation (Haversine formula)
            import math
            
            def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
                """Calculate distance between two points in kilometers"""
                R = 6371.0  # Earth radius in km
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return R * c
            
            # Filter by distance
            for category, items in all_content.items():
                for item in items:
                    location = item.get("location")
                    if location and isinstance(location, dict):
                        loc_lat = location.get("latitude")
                        loc_lng = location.get("longitude")
                        if loc_lat is not None and loc_lng is not None:
                            try:
                                distance = haversine_distance(latitude, longitude, float(loc_lat), float(loc_lng))
                                if distance <= radius_km:
                                    item_copy = dict(item)
                                    item_copy["distance_km"] = round(distance, 2)
                                    results.append(item_copy)
                            except (ValueError, TypeError):
                                continue
            
            # Sort by distance
            results.sort(key=lambda x: x.get("distance_km", float("inf")))
            return results
        except Exception as e:
            logger.error(f"❌ Error getting scraped content by location: {e}")
            return []
    
    async def get_scraped_content_by_event_date(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find scraped content with events in date range.
        Dates should be in ISO format (YYYY-MM-DD).
        """
        if not self._is_available():
            return []
        try:
            from datetime import datetime as dt
            
            all_content = await self.get_all_scraped_content()
            results = []
            
            for category, items in all_content.items():
                for item in items:
                    events = item.get("events", [])
                    if not events:
                        continue
                    
                    # Check if any event falls within date range
                    for event in events:
                        if not isinstance(event, dict):
                            continue
                        
                        event_start = event.get("start_date")
                        event_end = event.get("end_date") or event_start
                        
                        if not event_start:
                            continue
                        
                        try:
                            # Parse dates
                            event_start_dt = dt.fromisoformat(event_start.split("T")[0])
                            
                            # Check if event overlaps with query range
                            if start_date:
                                start_dt = dt.fromisoformat(start_date.split("T")[0])
                                if event_start_dt < start_dt:
                                    if event_end:
                                        event_end_dt = dt.fromisoformat(event_end.split("T")[0])
                                        if event_end_dt < start_dt:
                                            continue
                                    else:
                                        continue
                            
                            if end_date:
                                end_dt = dt.fromisoformat(end_date.split("T")[0])
                                if event_start_dt > end_dt:
                                    continue
                            
                            # Event matches date range
                            item_copy = dict(item)
                            item_copy["matched_event"] = event
                            results.append(item_copy)
                            break  # Only add item once even if multiple events match
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Error parsing event date: {e}")
                            continue
            
            return results
        except Exception as e:
            logger.error(f"❌ Error getting scraped content by event date: {e}")
            return []
    
    async def get_scraped_content_by_personality_traits(
        self, traits: Dict[str, float], min_match_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find scraped content matching personality traits.
        traits: {adventurous: 0.8, cultural: 0.6, ...}
        Returns items where personality_keywords align with provided traits.
        """
        if not self._is_available():
            return []
        try:
            all_content = await self.get_all_scraped_content()
            results = []
            
            for category, items in all_content.items():
                for item in items:
                    item_keywords = item.get("personality_keywords", {})
                    if not item_keywords or not isinstance(item_keywords, dict):
                        continue
                    
                    # Calculate match score
                    match_score = 0.0
                    matched_traits = 0
                    
                    for trait, user_score in traits.items():
                        if trait in item_keywords:
                            item_score = item_keywords[trait]
                            if isinstance(item_score, (int, float)) and isinstance(user_score, (int, float)):
                                # Score based on similarity (higher when both are high)
                                similarity = 1.0 - abs(user_score - item_score)
                                match_score += similarity * user_score  # Weight by user preference
                                matched_traits += 1
                    
                    if matched_traits > 0:
                        avg_match = match_score / matched_traits
                        if avg_match >= min_match_score:
                            item_copy = dict(item)
                            item_copy["personality_match_score"] = round(avg_match, 2)
                            results.append(item_copy)
            
            # Sort by match score (highest first)
            results.sort(key=lambda x: x.get("personality_match_score", 0), reverse=True)
            return results
        except Exception as e:
            logger.error(f"❌ Error getting scraped content by personality traits: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global instance
instantdb_client = InstantDBClient()
