"""User profile module - stores personality traits, preferences, travel history"""

import json
from datetime import datetime
from typing import Optional
from threading import Lock

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.bigquery_client import bigquery_client
from app.instantdb_client import instantdb_client
from app.models.interaction_log import InteractionLog, InteractionLogCreate


class PersonalityTraits(BaseModel):
    """User personality traits inferred from interactions"""

    adventurous: float = Field(default=0.5, ge=0.0, le=1.0)
    cultural: float = Field(default=0.5, ge=0.0, le=1.0)
    foodie: float = Field(default=0.5, ge=0.0, le=1.0)
    nature_lover: float = Field(default=0.5, ge=0.0, le=1.0)
    history_buff: float = Field(default=0.5, ge=0.0, le=1.0)
    social: float = Field(default=0.5, ge=0.0, le=1.0)


class UserPreferences(BaseModel):
    """User travel preferences"""

    budget_range: Optional[str] = None  # "budget", "mid-range", "luxury"
    travel_style: Optional[str] = None  # "solo", "couple", "family", "group"
    interests: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """User profile model"""

    user_id: str
    email: Optional[str] = None  # Optional - not stored in InstantDB, only used for compatibility
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    social_media_data: Optional[dict] = None
    travel_history: list[dict] = Field(default_factory=list)
    characteristics_summary: Optional[str] = None  # Summary of characteristics from SERP scraping
    source_links: list[str] = Field(default_factory=list)  # Links where information was found
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


# In-memory cache for personality data that's been analyzed but not yet saved to BigQuery
# This handles the case where BigQuery streaming buffer prevents immediate updates
_personality_cache: dict[str, PersonalityTraits] = {}
_cache_lock = Lock()


class UserProfileService:
    """Service for managing user profiles using BigQuery"""

    def _get_cached_personality(self, user_id: str) -> Optional[PersonalityTraits]:
        """Get personality from cache if available"""
        with _cache_lock:
            return _personality_cache.get(user_id)
    
    def _set_cached_personality(self, user_id: str, personality: PersonalityTraits):
        """Store personality in cache"""
        with _cache_lock:
            _personality_cache[user_id] = personality
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"💾 CACHE SET for {user_id}: {personality.model_dump()}")
            logger.info(f"💾 Cache size: {len(_personality_cache)} users")
    
    def _clear_cached_personality(self, user_id: str):
        """Clear personality from cache (after successful BigQuery update)"""
        with _cache_lock:
            _personality_cache.pop(user_id, None)

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID - uses InstantDB for real-time data"""
        try:
            # Try InstantDB first (real-time, no streaming buffer issues!)
            profile_data = await instantdb_client.get_user_profile(user_id)
            
            if not profile_data:
                # Fallback to BigQuery for historical data
                profile_data = await bigquery_client.get_user_profile(user_id)
            
            if not profile_data:
                return None
            
            # Map InstantDB 'id' field to 'user_id' (required by UserProfile model)
            # InstantDB uses 'id' as the primary key, but UserProfile expects 'user_id'
            if "id" in profile_data:
                if "user_id" not in profile_data:
                    profile_data["user_id"] = profile_data["id"]
                # Keep 'id' as well for compatibility, but ensure 'user_id' exists
            elif "user_id" not in profile_data:
                # If neither 'id' nor 'user_id' exists, use the query parameter
                profile_data["user_id"] = user_id
            
            # Ensure user_id is always set
            if "user_id" not in profile_data:
                profile_data["user_id"] = user_id
            
            # Parse JSON fields
            if profile_data.get("preferences") and isinstance(profile_data["preferences"], str):
                profile_data["preferences"] = json.loads(profile_data["preferences"])
            if profile_data.get("social_media_data") and isinstance(profile_data["social_media_data"], str):
                profile_data["social_media_data"] = json.loads(profile_data["social_media_data"])
            # Handle travel_history - can be None, string, or list
            if profile_data.get("travel_history") is None:
                profile_data["travel_history"] = []
            elif isinstance(profile_data["travel_history"], str):
                profile_data["travel_history"] = json.loads(profile_data["travel_history"])
            elif not isinstance(profile_data["travel_history"], list):
                profile_data["travel_history"] = []
            
            # Handle source_links - ensure it's always a list
            if profile_data.get("source_links") is None:
                profile_data["source_links"] = []
            elif isinstance(profile_data["source_links"], str):
                # If it's a JSON string, parse it
                try:
                    profile_data["source_links"] = json.loads(profile_data["source_links"])
                except:
                    # If parsing fails, treat as single URL
                    profile_data["source_links"] = [profile_data["source_links"]]
            elif not isinstance(profile_data["source_links"], list):
                profile_data["source_links"] = []
            
            # Build personality from individual columns
            # Log what we're getting from InstantDB/BigQuery
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"🔍 DEBUG: Profile data keys from DB for {user_id}: {list(profile_data.keys())}")
            
            # Extract personality fields and handle type conversion (InstantDB might return strings)
            def safe_float(value, default=0.5):
                """Safely convert value to float, handling strings and None"""
                if value is None:
                    return default
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                return default
            
            adventurous_val = safe_float(profile_data.get("adventurous"), 0.5)
            cultural_val = safe_float(profile_data.get("cultural"), 0.5)
            foodie_val = safe_float(profile_data.get("foodie"), 0.5)
            nature_lover_val = safe_float(profile_data.get("nature_lover"), 0.5)
            history_buff_val = safe_float(profile_data.get("history_buff"), 0.5)
            social_val = safe_float(profile_data.get("social"), 0.5)
            
            logger.warning(f"🔍 DEBUG: Personality fields from DB (raw) for {user_id}: adventurous={profile_data.get('adventurous')} ({type(profile_data.get('adventurous')).__name__}), cultural={profile_data.get('cultural')} ({type(profile_data.get('cultural')).__name__}), foodie={profile_data.get('foodie')} ({type(profile_data.get('foodie')).__name__}), nature_lover={profile_data.get('nature_lover')} ({type(profile_data.get('nature_lover')).__name__}), history_buff={profile_data.get('history_buff')} ({type(profile_data.get('history_buff')).__name__}), social={profile_data.get('social')} ({type(profile_data.get('social')).__name__})")
            logger.warning(f"🔍 DEBUG: Personality fields (converted) for {user_id}: adventurous={adventurous_val}, cultural={cultural_val}, foodie={foodie_val}, nature_lover={nature_lover_val}, history_buff={history_buff_val}, social={social_val}")
            
            personality = PersonalityTraits(
                adventurous=adventurous_val,
                cultural=cultural_val,
                foodie=foodie_val,
                nature_lover=nature_lover_val,
                history_buff=history_buff_val,
                social=social_val,
            )
            
            # Check if we have a cached personality
            personality_dict = personality.model_dump()
            all_defaults = all(v == 0.5 for v in personality_dict.values())
            
            if all_defaults:
                logger.warning(f"⚠️  Personality all defaults (0.5) for {user_id} from DB, checking cache...")
                logger.debug(f"   DB values: {personality_dict}")
                cached_personality = self._get_cached_personality(user_id)
                if cached_personality:
                    logger.info(f"✅ Found cached personality for {user_id}: {cached_personality.model_dump()}")
                    personality = cached_personality
                else:
                    logger.warning(f"❌ No cached personality for {user_id} - personality analysis may not have completed")
                    # Log what InstantDB actually returned to help debug
                    logger.debug(f"   InstantDB profile data sample: {str(profile_data)[:1000]}")
            else:
                logger.info(f"✅ InstantDB/BigQuery has personality for {user_id}: {personality_dict}")
            
            profile_data["personality"] = personality
            
            # Build preferences
            prefs_dict = profile_data.get("preferences", {})
            if isinstance(prefs_dict, str):
                prefs_dict = json.loads(prefs_dict)
            preferences = UserPreferences(**prefs_dict) if prefs_dict else UserPreferences()
            profile_data["preferences"] = preferences
            
            # Validate that user_id exists before creating UserProfile
            if "user_id" not in profile_data:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"❌ Profile data missing user_id field. Keys: {list(profile_data.keys())}")
                logger.error(f"   Profile data sample: {str(profile_data)[:500]}")
                # Try to set it from the query parameter
                profile_data["user_id"] = user_id
            
            return UserProfile(**profile_data)
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error getting profile for {user_id}: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Log the profile_data structure if available
            try:
                if 'profile_data' in locals():
                    logger.error(f"   Profile data keys: {list(profile_data.keys()) if isinstance(profile_data, dict) else 'not a dict'}")
            except:
                pass
            return None

    async def get_profile_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email"""
        # BigQuery doesn't have a direct email lookup in our current implementation
        # We'll need to add a query for this
        try:
            from app.bigquery_client import bigquery_client
            if not bigquery_client._is_available():
                return None
                
            query = f"""
            SELECT *
            FROM `{bigquery_client.project_id}.{bigquery_client.dataset_id}.user_profiles`
            WHERE email = @email
            LIMIT 1
            """
            
            from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("email", "STRING", email)
                ]
            )
            
            query_job = bigquery_client.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                profile_data = dict(row)
                # Map 'id' to 'user_id' if needed
                if "id" in profile_data and "user_id" not in profile_data:
                    profile_data["user_id"] = profile_data["id"]
                # Parse JSON fields and build profile (same as get_profile)
                if profile_data.get("preferences") and isinstance(profile_data["preferences"], str):
                    profile_data["preferences"] = json.loads(profile_data["preferences"])
                if profile_data.get("social_media_data") and isinstance(profile_data["social_media_data"], str):
                    profile_data["social_media_data"] = json.loads(profile_data["social_media_data"])
                # Handle travel_history - can be None, string, or list
                if profile_data.get("travel_history") is None:
                    profile_data["travel_history"] = []
                elif isinstance(profile_data["travel_history"], str):
                    profile_data["travel_history"] = json.loads(profile_data["travel_history"])
                elif not isinstance(profile_data["travel_history"], list):
                    profile_data["travel_history"] = []
                
                # Handle source_links - ensure it's always a list
                if profile_data.get("source_links") is None:
                    profile_data["source_links"] = []
                elif isinstance(profile_data["source_links"], str):
                    try:
                        profile_data["source_links"] = json.loads(profile_data["source_links"])
                    except:
                        profile_data["source_links"] = [profile_data["source_links"]]
                elif not isinstance(profile_data["source_links"], list):
                    profile_data["source_links"] = []
                
                personality = PersonalityTraits(
                    adventurous=profile_data.get("adventurous", 0.5),
                    cultural=profile_data.get("cultural", 0.5),
                    foodie=profile_data.get("foodie", 0.5),
                    nature_lover=profile_data.get("nature_lover", 0.5),
                    history_buff=profile_data.get("history_buff", 0.5),
                    social=profile_data.get("social", 0.5),
                )
                
                # Check if we have a cached personality (analyzed but not yet saved to BigQuery)
                # Use cached personality if BigQuery values are all defaults (0.5)
                personality_dict = personality.model_dump()
                all_defaults = all(v == 0.5 for v in personality_dict.values())
                user_id = profile_data.get("user_id")
                
                import logging
                logger = logging.getLogger(__name__)
                if all_defaults and user_id:
                    logger.info(f"⚠️  BigQuery personality all defaults for {user_id} (by email), checking cache...")
                    cached_personality = self._get_cached_personality(user_id)
                    if cached_personality:
                        logger.info(f"✅ Found cached personality for {user_id}: {cached_personality.model_dump()}")
                        personality = cached_personality
                    else:
                        logger.info(f"❌ No cached personality for {user_id}")
                elif user_id:
                    logger.info(f"✅ BigQuery has personality for {user_id}: {personality_dict}")
                
                profile_data["personality"] = personality
                
                prefs_dict = profile_data.get("preferences", {})
                if isinstance(prefs_dict, str):
                    prefs_dict = json.loads(prefs_dict)
                preferences = UserPreferences(**prefs_dict) if prefs_dict else UserPreferences()
                profile_data["preferences"] = preferences
                
                return UserProfile(**profile_data)
            return None
        except Exception as e:
            print(f"Error getting profile by email from BigQuery: {e}")
            return None

    async def create_profile(
        self, 
        user_id: str,
        email: Optional[str] = None,  # Optional - not stored in InstantDB
        name: Optional[str] = None,
        phone_number: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[UserProfile]:
        """Create a new user profile - uses InstantDB for instant creation"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Check if profile already exists
            existing = await self.get_profile(user_id)
            if existing:
                logger.info(f"Profile already exists for user_id: {user_id}")
                return existing
            
            profile = UserProfile(
                user_id=user_id,
                email=email,
                name=name,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
            )
            
            # Use mode='json' to serialize datetime objects to strings
            # Exclude email - not stored in InstantDB
            profile_dict = profile.model_dump(exclude={"personality", "preferences", "email"}, mode='json')
            profile_dict["personality"] = profile.personality.model_dump(mode='json')
            profile_dict["preferences"] = profile.preferences.model_dump(mode='json')
            
            logger.info(f"Creating profile in InstantDB: user_id={user_id}, phone={phone_number}")
            logger.info(f"   Profile data keys: {list(profile_dict.keys())}")
            
            # Create in InstantDB (instant, no 90-minute lock!)
            success = await instantdb_client.create_user_profile(user_id, profile_dict)
            
            logger.info(f"   InstantDB create_user_profile returned: {success}")
            
            if success:
                logger.info(f"✅ Profile created instantly in InstantDB, fetching...")
                # Retry fetching the profile with exponential backoff
                import asyncio
                created_profile = None
                for attempt in range(5):  # Try up to 5 times
                    await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s, 0.8s, 1.0s
                    created_profile = await self.get_profile(user_id)
                    if created_profile:
                        logger.info(f"✅ Profile verified in InstantDB after {attempt + 1} attempt(s): {user_id}")
                        break
                    else:
                        # This is expected during retries - profile might not be queryable yet
                        logger.debug(f"   Profile not found on attempt {attempt + 1}/5, retrying... (this is normal)")
                
                if created_profile:
                    logger.info(f"✅ Profile verified in InstantDB: {user_id}")
                    # BigQuery disabled - using InstantDB as primary database
                    # (BigQuery streaming buffer issues and not needed with InstantDB)
                else:
                    logger.warning(f"⚠️  Profile created but not found after 5 retries: {user_id}")
                    # Still return None - the profile might exist but query is failing
                return created_profile
            else:
                logger.error(f"❌ InstantDB create_user_profile returned False for {user_id}")
                return None
        except Exception as e:
            import traceback
            logger.error(f"❌ Error creating profile in InstantDB: {e}", exc_info=True)
            print(f"❌ Error creating profile: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None

    async def update_personality(
        self, 
        user_id: str, 
        traits: PersonalityTraits,
        characteristics_summary: Optional[str] = None,
        source_links: Optional[list] = None
    ) -> Optional[UserProfile]:
        """Update user personality traits - uses InstantDB for instant update (NO 90-MINUTE LOCK!)"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Store in cache immediately (for real-time access)
        self._set_cached_personality(user_id, traits)
        logger.info(f"💾 Stored personality in cache for {user_id}: {traits.model_dump()}")
        
        try:
            update_data = {
                "adventurous": traits.adventurous,
                "cultural": traits.cultural,
                "foodie": traits.foodie,
                "nature_lover": traits.nature_lover,
                "history_buff": traits.history_buff,
                "social": traits.social,
            }
            
            # Add characteristics summary and source links if provided
            if characteristics_summary:
                update_data["characteristics_summary"] = characteristics_summary
            if source_links:
                update_data["source_links"] = source_links
            
            # First, ensure the profile exists
            existing_profile = await self.get_profile(user_id)
            if not existing_profile:
                logger.warning(f"⚠️  Profile not found for {user_id}, creating it first...")
                # Create a minimal profile if it doesn't exist
                try:
                    minimal_profile = await self.create_profile(
                        user_id=user_id,
                        name="User",
                        phone_number=None,
                        first_name=None,
                        last_name=None
                    )
                    if not minimal_profile:
                        logger.error(f"❌ Failed to create profile for {user_id}, cannot update personality")
                        return None
                except Exception as create_error:
                    logger.error(f"❌ Error creating profile for {user_id}: {create_error}")
                    return None
            
            logger.warning(f"💾 Updating personality in InstantDB for {user_id}: {update_data}")
            
            # Update in InstantDB INSTANTLY (no streaming buffer!)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            
            if success:
                logger.warning(f"✅ InstantDB update_user_profile returned success=True for {user_id}")
                # Clear cache after successful InstantDB update
                self._clear_cached_personality(user_id)
                # Wait longer for InstantDB transaction to complete and be queryable
                # InstantDB transactions can take a moment to propagate
                import asyncio
                await asyncio.sleep(2.0)  # Increased from 0.5 to 2.0 seconds
                
                # Retry querying with exponential backoff if still getting defaults
                updated_profile = None
                for retry in range(3):
                    updated_profile = await self.get_profile(user_id)
                    if updated_profile:
                        personality_dict = updated_profile.personality.model_dump()
                        # Check if we got meaningful traits (not all defaults)
                        all_defaults = all(v == 0.5 for v in personality_dict.values())
                        if not all_defaults:
                            logger.warning(f"✅ Got non-default personality on retry {retry + 1}")
                            break
                        else:
                            logger.warning(f"⚠️ Retry {retry + 1}: Still getting defaults, waiting more...")
                            await asyncio.sleep(1.0 * (retry + 1))  # Exponential backoff: 1s, 2s, 3s
                    else:
                        await asyncio.sleep(1.0)
                if updated_profile:
                    saved_personality = updated_profile.personality.model_dump()
                    logger.warning(f"✅ Personality updated instantly in InstantDB for {user_id}")
                    logger.warning(f"   Retrieved personality after save: {saved_personality}")
                    
                    # Verify it's not all defaults
                    all_defaults = all(v == 0.5 for v in saved_personality.values())
                    if all_defaults:
                        logger.error(f"❌ CRITICAL: After saving, retrieved personality is STILL all defaults!")
                        logger.error(f"   This means InstantDB query is not returning saved values!")
                    else:
                        logger.warning(f"✅ Verified: Saved personality has meaningful traits")
                    return updated_profile
                else:
                    logger.error(f"❌ Failed to retrieve profile after InstantDB update for {user_id}")
                    # Return profile with cached personality as fallback
                    profile = await self.get_profile(user_id)
                    if profile:
                        profile.personality = traits
                    return profile
            else:
                logger.error(f"❌ InstantDB update_user_profile returned success=False for {user_id}")
                logger.error(f"   Personality was NOT saved to InstantDB!")
                logger.info(f"💾 Personality remains in cache for {user_id} - will be used immediately")
                # Return profile with cached personality
                profile = await self.get_profile(user_id)
                if profile:
                    profile.personality = traits
                return profile
        except Exception as e:
            import traceback
            logger.error(f"❌ Error updating personality in InstantDB: {e}", exc_info=True)
            print(f"❌ Error updating personality: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            # Return profile with cached personality even on error
            profile = await self.get_profile(user_id)
            if profile:
                profile.personality = traits
            return profile

    async def update_preferences(
        self, user_id: str, preferences: UserPreferences
    ) -> Optional[UserProfile]:
        """Update user preferences"""
        try:
            update_data = {
                "preferences": preferences.model_dump()
            }
            
            # Use InstantDB (primary database)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            logger.error(f"Error updating preferences in InstantDB: {e}")
            return None

    async def add_travel_history(self, user_id: str, history_item: dict) -> Optional[UserProfile]:
        """Add an item to travel history"""
        try:
            profile = await self.get_profile(user_id)
            if not profile:
                return None
            
            travel_history = profile.travel_history or []
            travel_history.append(history_item)
            
            update_data = {
                "travel_history": travel_history
            }
            
            # Use InstantDB (primary database)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            logger.error(f"Error adding travel history in InstantDB: {e}")
            return None

    async def update_name(self, user_id: str, name: str) -> Optional[UserProfile]:
        """Update the stored display name for a user"""
        try:
            update_data = {"name": name}
            # Use InstantDB (primary database)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            logger.error(f"Error updating name in InstantDB: {e}")
            return None

    async def update_social_media_data(
        self, user_id: str, social_media_data: dict
    ) -> Optional[UserProfile]:
        """Update social media data"""
        try:
            update_data = {"social_media_data": social_media_data}
            # Use InstantDB (primary database)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            logger.error(f"Error updating social media data in InstantDB: {e}")
            return None

    async def log_interaction(self, log: InteractionLogCreate) -> bool:
        """Log user interaction"""
        try:
            log_data = {
                "user_id": log.user_id,
                "interaction_type": log.interaction_type,
                "content": log.content,
                "metadata": log.metadata,
                "timestamp": datetime.utcnow(),
            }
            return await bigquery_client.insert_interaction_log(log_data)
        except Exception as e:
            print(f"Error logging interaction to BigQuery: {e}")
            return False

    async def get_interaction_history(self, user_id: str, limit: int = 100) -> list[dict]:
        """Get user interaction history"""
        try:
            return await bigquery_client.get_interaction_history(user_id, limit)
        except Exception as e:
            print(f"Error getting interaction history from BigQuery: {e}")
            return []
