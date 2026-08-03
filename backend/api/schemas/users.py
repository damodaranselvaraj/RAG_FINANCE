"""
Pydantic schemas for GET /users/{user_id}/profile.
"""
from datetime import datetime
from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    created_at: datetime
    profile_json: dict = {}
