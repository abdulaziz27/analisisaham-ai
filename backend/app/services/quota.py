"""
Quota Service
Handles user quota checking and management using SQLAlchemy ORM
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.app.models.database import UserQuota
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default free tier quota
DEFAULT_FREE_QUOTA = 3


async def check_quota(user_id: str, db: Session) -> bool:
    """
    Check if user has remaining quota.
    
    Args:
        user_id: Telegram user ID
        db: Database session
    
    Returns:
        True if user has quota, False otherwise
    """
    try:
        quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
        
        if quota is None:
            # User doesn't exist, create with default quota
            quota = UserQuota(
                user_id=user_id,
                requests_remaining=DEFAULT_FREE_QUOTA,
                total_requests=0
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)
            logger.info(f"Created new user quota for {user_id} with {DEFAULT_FREE_QUOTA} requests")
            return True
        
        return quota.requests_remaining > 0
    
    except Exception as e:
        logger.error(f"Error checking quota for user {user_id}: {str(e)}")
        db.rollback()
        # Fail-closed: Return False on error to protect resources
        return False


async def get_quota_info(
    user_id: str,
    db: Session,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None,
    is_premium: Optional[bool] = None
) -> Optional[dict]:
    """
    Get detailed quota information for user and update user info.
    
    Args:
        user_id: Telegram user ID
        db: Database session
        username: Optional username to update
        first_name: Optional first name to update
        last_name: Optional last name to update
        language_code: Optional language code to update
        is_premium: Optional premium status to update
    
    Returns:
        Dict with 'remaining' and 'total' keys, or None on error
    """
    try:
        quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
        
        # Update user info if provided
        if quota:
            if username is not None:
                quota.username = username
            if first_name is not None:
                quota.first_name = first_name
            if last_name is not None:
                quota.last_name = last_name
            if language_code is not None:
                quota.language_code = language_code
            if is_premium is not None:
                quota.is_premium = is_premium
        else:
            # Create new user with provided info
            quota = UserQuota(
                user_id=user_id,
                requests_remaining=DEFAULT_FREE_QUOTA,
                total_requests=0,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_premium=is_premium or False
            )
            db.add(quota)
        
        db.commit()
        db.refresh(quota)
        
        return {
            "remaining": quota.requests_remaining,
            "total": quota.total_requests
        }
    
    except Exception as e:
        logger.error(f"Error getting quota info for user {user_id}: {str(e)}")
        db.rollback()
        return None


async def decrement_quota(user_id: str, db: Session) -> bool:
    """
    Decrement user's quota atomically.
    
    Args:
        user_id: Telegram user ID
        db: Database session
    
    Returns:
        True if quota was successfully decremented (user had quota).
        False if user had no quota remaining.
    """
    try:
        # Ensure user exists (idempotent)
        quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
        
        if quota is None:
            quota = UserQuota(
                user_id=user_id,
                requests_remaining=DEFAULT_FREE_QUOTA,
                total_requests=0
            )
            db.add(quota)
            db.flush()  # Flush to get ID but don't commit yet
        
        # Atomic update: Decrement ONLY if > 0
        if quota.requests_remaining > 0:
            quota.requests_remaining -= 1
            quota.total_requests += 1
            db.commit()
            logger.info(f"Decremented quota for user {user_id}. Remaining: {quota.requests_remaining}")
            return True
        else:
            db.commit()  # Commit even if no decrement (for consistency)
            logger.warning(f"User {user_id} tried to decrement but has 0 quota")
            return False
    
    except Exception as e:
        logger.error(f"Error decrementing quota for user {user_id}: {str(e)}")
        db.rollback()
        # Fail-closed: Return False on error to protect resources
        return False
