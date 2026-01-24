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
    email: EmailStr
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    social_media_data: Optional[dict] = None
    travel_history: list[dict] = Field(default_factory=list)
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
            
            # Build personality from individual columns
            personality = PersonalityTraits(
                adventurous=profile_data.get("adventurous", 0.5),
                cultural=profile_data.get("cultural", 0.5),
                foodie=profile_data.get("foodie", 0.5),
                nature_lover=profile_data.get("nature_lover", 0.5),
                history_buff=profile_data.get("history_buff", 0.5),
                social=profile_data.get("social", 0.5),
            )
            
            # Check if we have a cached personality
            personality_dict = personality.model_dump()
            all_defaults = all(v == 0.5 for v in personality_dict.values())
            
            import logging
            logger = logging.getLogger(__name__)
            if all_defaults:
                logger.info(f"⚠️  Personality all defaults for {user_id}, checking cache...")
                cached_personality = self._get_cached_personality(user_id)
                if cached_personality:
                    logger.info(f"✅ Found cached personality for {user_id}: {cached_personality.model_dump()}")
                    personality = cached_personality
                else:
                    logger.info(f"❌ No cached personality for {user_id}")
            else:
                logger.info(f"✅ InstantDB has personality for {user_id}: {personality_dict}")
            
            profile_data["personality"] = personality
            
            # Build preferences
            prefs_dict = profile_data.get("preferences", {})
            if isinstance(prefs_dict, str):
                prefs_dict = json.loads(prefs_dict)
            preferences = UserPreferences(**prefs_dict) if prefs_dict else UserPreferences()
            profile_data["preferences"] = preferences
            
            return UserProfile(**profile_data)
        except Exception as e:
            print(f"Error getting profile: {e}")
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
        email: EmailStr, 
        user_id: str, 
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
            profile_dict = profile.model_dump(exclude={"personality", "preferences"}, mode='json')
            profile_dict["personality"] = profile.personality.model_dump(mode='json')
            profile_dict["preferences"] = profile.preferences.model_dump(mode='json')
            
            logger.info(f"Creating profile in InstantDB: user_id={user_id}, email={email}")
            
            # Create in InstantDB (instant, no 90-minute lock!)
            success = await instantdb_client.create_user_profile(user_id, profile_dict)
            
            if success:
                logger.info(f"✅ Profile created instantly in InstantDB, fetching...")
                created_profile = await self.get_profile(user_id)
                if created_profile:
                    logger.info(f"✅ Profile verified in InstantDB: {user_id}")
                    # Also save to BigQuery asynchronously for analytics
                    try:
                        await bigquery_client.create_user_profile(profile_dict)
                        logger.info(f"💾 Profile also saved to BigQuery for analytics")
                    except Exception as bq_error:
                        logger.warning(f"⚠️  BigQuery save skipped (not critical): {bq_error}")
                else:
                    logger.warning(f"⚠️  Profile created but not found when fetching: {user_id}")
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
        self, user_id: str, traits: PersonalityTraits
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
            
            logger.info(f"Updating personality in InstantDB for {user_id}: {update_data}")
            
            # Update in InstantDB INSTANTLY (no streaming buffer!)
            success = await instantdb_client.update_user_profile(user_id, update_data)
            
            if success:
                # Clear cache after successful InstantDB update
                self._clear_cached_personality(user_id)
                updated_profile = await self.get_profile(user_id)
                if updated_profile:
                    logger.info(f"✅ Personality updated instantly in InstantDB for {user_id}")
                    # Also save to BigQuery asynchronously for analytics
                    try:
                        await bigquery_client.update_user_profile(user_id, update_data)
                        logger.info(f"💾 Personality also saved to BigQuery for analytics")
                    except Exception as bq_error:
                        logger.warning(f"⚠️  BigQuery save failed (non-critical): {bq_error}")
                else:
                    logger.warning(f"⚠️  Personality update succeeded but profile not found: {user_id}")
                return updated_profile
            else:
                logger.error(f"❌ InstantDB update_user_profile returned False for {user_id}")
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
            
            success = await bigquery_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error updating preferences in BigQuery: {e}")
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
            
            success = await bigquery_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error adding travel history in BigQuery: {e}")
            return None

    async def update_name(self, user_id: str, name: str) -> Optional[UserProfile]:
        """Update the stored display name for a user"""
        try:
            update_data = {"name": name}
            success = await bigquery_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error updating name in BigQuery: {e}")
            return None

    async def update_social_media_data(
        self, user_id: str, social_media_data: dict
    ) -> Optional[UserProfile]:
        """Update social media data"""
        try:
            update_data = {"social_media_data": social_media_data}
            success = await bigquery_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error updating social media data in BigQuery: {e}")
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
