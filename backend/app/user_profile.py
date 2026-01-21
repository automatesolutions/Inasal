"""User profile module - stores personality traits, preferences, travel history"""

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.bigquery_client import bigquery_client
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


class UserProfileService:
    """Service for managing user profiles using BigQuery"""

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            profile_data = await bigquery_client.get_user_profile(user_id)
            if not profile_data:
                return None
            
            # Parse JSON fields
            if profile_data.get("preferences") and isinstance(profile_data["preferences"], str):
                profile_data["preferences"] = json.loads(profile_data["preferences"])
            if profile_data.get("social_media_data") and isinstance(profile_data["social_media_data"], str):
                profile_data["social_media_data"] = json.loads(profile_data["social_media_data"])
            if profile_data.get("travel_history") and isinstance(profile_data["travel_history"], str):
                profile_data["travel_history"] = json.loads(profile_data["travel_history"])
            
            # Build personality from individual columns
            personality = PersonalityTraits(
                adventurous=profile_data.get("adventurous", 0.5),
                cultural=profile_data.get("cultural", 0.5),
                foodie=profile_data.get("foodie", 0.5),
                nature_lover=profile_data.get("nature_lover", 0.5),
                history_buff=profile_data.get("history_buff", 0.5),
                social=profile_data.get("social", 0.5),
            )
            profile_data["personality"] = personality
            
            # Build preferences
            prefs_dict = profile_data.get("preferences", {})
            if isinstance(prefs_dict, str):
                prefs_dict = json.loads(prefs_dict)
            preferences = UserPreferences(**prefs_dict) if prefs_dict else UserPreferences()
            profile_data["preferences"] = preferences
            
            return UserProfile(**profile_data)
        except Exception as e:
            print(f"Error getting profile from BigQuery: {e}")
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
                if profile_data.get("travel_history") and isinstance(profile_data["travel_history"], str):
                    profile_data["travel_history"] = json.loads(profile_data["travel_history"])
                
                personality = PersonalityTraits(
                    adventurous=profile_data.get("adventurous", 0.5),
                    cultural=profile_data.get("cultural", 0.5),
                    foodie=profile_data.get("foodie", 0.5),
                    nature_lover=profile_data.get("nature_lover", 0.5),
                    history_buff=profile_data.get("history_buff", 0.5),
                    social=profile_data.get("social", 0.5),
                )
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
        """Create a new user profile"""
        try:
            # Check if profile already exists
            existing = await self.get_profile(user_id)
            if existing:
                return existing
            
            profile = UserProfile(
                user_id=user_id,
                email=email,
                name=name,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
            )
            
            profile_dict = profile.model_dump(exclude={"personality", "preferences"})
            profile_dict["personality"] = profile.personality.model_dump()
            profile_dict["preferences"] = profile.preferences.model_dump()
            
            success = await bigquery_client.create_user_profile(profile_dict)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error creating profile in BigQuery: {e}")
            return None

    async def update_personality(
        self, user_id: str, traits: PersonalityTraits
    ) -> Optional[UserProfile]:
        """Update user personality traits"""
        try:
            update_data = {
                "personality": traits.model_dump()
            }
            
            success = await bigquery_client.update_user_profile(user_id, update_data)
            if success:
                return await self.get_profile(user_id)
            return None
        except Exception as e:
            print(f"Error updating personality in BigQuery: {e}")
            return None

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
