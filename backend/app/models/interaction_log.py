"""Interaction log models for tracking user behavior"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InteractionLog(BaseModel):
    """User interaction log model"""

    user_id: str
    interaction_type: str  # "chat", "search", "view_destination", "like", "bookmark"
    content: dict = Field(default_factory=dict)  # Flexible content structure
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InteractionLogCreate(BaseModel):
    """Schema for creating interaction logs"""

    user_id: str
    interaction_type: str
    content: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

