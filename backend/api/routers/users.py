"""
GET /users/{user_id}/profile  — retrieve a user's persisted profile / intent store.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.config import Settings, get_settings
from api.schemas.users import UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/{user_id}/profile",
    response_model=UserProfile,
    summary="Get user profile and intent store",
)
async def get_user_profile(
    user_id: str,
    settings: Settings = Depends(get_settings),
) -> UserProfile:
    """
    Returns the profile_json for the given user_id.
    Stub — replace with a SQLite lookup once the memory layer is built:
        from memory.db import get_db
        user = get_user(user_id, db=next(get_db()))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    """
    logger.info("profile request user=%s", user_id)

    # Stub: return an empty profile so the endpoint is testable immediately.
    return UserProfile(
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        profile_json={},
    )
