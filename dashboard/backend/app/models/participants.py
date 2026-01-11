"""
Participant Models

Request and response models for participant endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ParticipantInit(BaseModel):
    """Request model for initializing a participant."""
    event_code: str
    username: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    project_id: Optional[str] = None


class ParticipantInitResponse(BaseModel):
    """Response model for participant initialization."""
    participant_id: str
    username: str
    event_code: str
    starting_x: int
    starting_y: int


class ParticipantRegister(BaseModel):
    """Request model for completing participant registration."""
    participant_id: str
    suit_color: Optional[str] = None
    appearance: Optional[str] = None


class ParticipantResponse(BaseModel):
    """Response model for participant information."""
    participant_id: str
    username: str
    event_code: str
    x: int
    y: int
    location_confirmed: bool = False
    portrait_url: Optional[str] = None
    icon_url: Optional[str] = None
    suit_color: Optional[str] = None
    registered_at: Optional[datetime] = None
    active: bool = True
    evidence_urls: Optional[dict] = None
    level_0_complete: Optional[bool] = None
    level_1_complete: Optional[bool] = None
    level_2_complete: Optional[bool] = None
    level_3_complete: Optional[bool] = None
    level_4_complete: Optional[bool] = None
    level_5_complete: Optional[bool] = None


class ParticipantUpdate(BaseModel):
    """Request model for updating participant fields (including overrides)."""
    level_0_complete: Optional[bool] = None
    level_1_complete: Optional[bool] = None
    level_2_complete: Optional[bool] = None
    level_3_complete: Optional[bool] = None
    level_4_complete: Optional[bool] = None
    level_5_complete: Optional[bool] = None
    completion_percentage: Optional[int] = None


class UsernameCheckResponse(BaseModel):
    """Response model for username availability check."""
    available: bool
    username: str
