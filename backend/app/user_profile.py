"""User profile module - stores personality traits, preferences, travel history"""

from datetime import datetime
from typing import Optional
from bson import ObjectId

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.database import get_database, HAS_MONGODB
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

    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    email: EmailStr
    name: Optional[str] = None
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    travel_history: list[dict] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class UserProfileService:
    """Service for managing user profiles"""

    COLLECTION_NAME = "user_profiles"

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            profile_doc = await collection.find_one({"user_id": user_id})
            if not profile_doc:
                return None
            
            # Convert MongoDB ObjectId to string
            if "_id" in profile_doc:
                profile_doc["_id"] = str(profile_doc["_id"])
            
            return UserProfile(**profile_doc)
        except Exception:
            return None  # Fallback to Strapi

    async def get_profile_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            profile_doc = await collection.find_one({"email": email})
            if not profile_doc:
                return None
            
            if "_id" in profile_doc:
                profile_doc["_id"] = str(profile_doc["_id"])
            
            return UserProfile(**profile_doc)
        except Exception:
            return None  # Fallback to Strapi

    async def create_profile(self, email: EmailStr, user_id: str, name: Optional[str] = None) -> Optional[UserProfile]:
        """Create a new user profile"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            # Check if profile already exists
            existing = await self.get_profile(user_id)
            if existing:
                return existing
            
            profile = UserProfile(
                user_id=user_id,
                email=email,
                name=name,
            )
            
            profile_dict = profile.model_dump(exclude={"id"}, by_alias=True)
            result = await collection.insert_one(profile_dict)
            
            # Fetch the created profile
            created_doc = await collection.find_one({"_id": result.inserted_id})
            if created_doc and "_id" in created_doc:
                created_doc["_id"] = str(created_doc["_id"])
            
            return UserProfile(**created_doc)
        except Exception:
            return None  # Fallback to Strapi

    async def update_personality(
        self, user_id: str, traits: PersonalityTraits
    ) -> Optional[UserProfile]:
        """Update user personality traits"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            update_data = {
                "$set": {
                    "personality": traits.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await collection.update_one(
                {"user_id": user_id},
                update_data
            )
            
            if result.modified_count == 0:
                return None
            
            return await self.get_profile(user_id)
        except Exception:
            return None  # Fallback to Strapi

    async def update_preferences(
        self, user_id: str, preferences: UserPreferences
    ) -> Optional[UserProfile]:
        """Update user preferences"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            update_data = {
                "$set": {
                    "preferences": preferences.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await collection.update_one(
                {"user_id": user_id},
                update_data
            )
            
            if result.modified_count == 0:
                return None
            
            return await self.get_profile(user_id)
        except Exception:
            return None  # Fallback to Strapi

    async def add_travel_history(self, user_id: str, history_item: dict) -> Optional[UserProfile]:
        """Add an item to travel history"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]
            
            update_data = {
                "$push": {"travel_history": history_item},
                "$set": {"updated_at": datetime.utcnow()}
            }
            
            result = await collection.update_one(
                {"user_id": user_id},
                update_data
            )
            
            if result.modified_count == 0:
                return None
            
            return await self.get_profile(user_id)
        except Exception:
            return None  # Fallback to Strapi

    async def update_name(self, user_id: str, name: str) -> Optional[UserProfile]:
        """Update the stored display name for a user"""
        if not HAS_MONGODB:
            return None  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db[self.COLLECTION_NAME]

            result = await collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "name": name,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            if result.modified_count == 0:
                return None

            return await self.get_profile(user_id)
        except Exception:
            return None  # Fallback to Strapi

    async def log_interaction(self, log: InteractionLogCreate) -> bool:
        """Log user interaction"""
        if not HAS_MONGODB:
            return False  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db["interaction_logs"]
            
            interaction = InteractionLog(**log.model_dump())
            await collection.insert_one(interaction.model_dump(by_alias=True))
            return True
        except Exception:
            return False  # Fallback to Strapi

    async def get_interaction_history(self, user_id: str, limit: int = 100) -> list[dict]:
        """Get user interaction history"""
        if not HAS_MONGODB:
            return []  # Use Strapi instead
        
        try:
            db = get_database()
            collection = db["interaction_logs"]
            
            cursor = collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
            logs = []
            async for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                if "timestamp" in doc and isinstance(doc["timestamp"], datetime):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                logs.append(doc)
            
            return logs
        except Exception:
            return []  # Fallback to Strapi

