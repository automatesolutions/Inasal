"""User profile module - stores personality traits, preferences, travel history"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class PersonalityTraits(BaseModel):
    """User personality traits inferred from interactions"""

    adventurous: float = 0.5  # 0.0 to 1.0
    cultural: float = 0.5
    foodie: float = 0.5
    nature_lover: float = 0.5
    history_buff: float = 0.5
    social: float = 0.5


class UserPreferences(BaseModel):
    """User travel preferences"""

    budget_range: Optional[str] = None  # "budget", "mid-range", "luxury"
    travel_style: Optional[str] = None  # "solo", "couple", "family", "group"
    interests: list[str] = []
    accessibility_needs: list[str] = []


class UserProfile(BaseModel):
    """User profile model"""

    user_id: str
    email: EmailStr
    name: Optional[str] = None
    personality: PersonalityTraits = PersonalityTraits()
    preferences: UserPreferences = UserPreferences()
    travel_history: list[dict] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserProfileService:
    """Service for managing user profiles"""

    def __init__(self):
        # TODO: Initialize MongoDB connection
        pass

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        # TODO: Implement MongoDB query
        return None

    async def create_profile(self, email: EmailStr, user_id: str) -> UserProfile:
        """Create a new user profile"""
        # TODO: Implement MongoDB insert
        profile = UserProfile(user_id=user_id, email=email)
        return profile

    async def update_personality(
        self, user_id: str, traits: PersonalityTraits
    ) -> UserProfile:
        """Update user personality traits"""
        # TODO: Implement MongoDB update
        profile = await self.get_profile(user_id)
        if profile:
            profile.personality = traits
        return profile

    async def update_preferences(
        self, user_id: str, preferences: UserPreferences
    ) -> UserProfile:
        """Update user preferences"""
        # TODO: Implement MongoDB update
        profile = await self.get_profile(user_id)
        if profile:
            profile.preferences = preferences
        return profile

