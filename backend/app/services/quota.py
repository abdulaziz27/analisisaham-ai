"""
Quota Service
Handles user quota checking and management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Database connection
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_MIN,
    max_overflow=settings.DB_POOL_MAX - settings.DB_POOL_MIN
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_quota_tables():
    """Ensure quota table exists"""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_quotas (
                    user_id VARCHAR(255) PRIMARY KEY,
                    requests_remaining INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            logger.info("Checked/Created user_quotas table")
    except Exception as e:
        logger.error(f"Error creating quota tables: {str(e)}")

# Initialize tables on module load
ensure_quota_tables()


async def check_quota(user_id: str) -> bool:
    """
    Check if user has remaining quota
    """
    try:
        with engine.connect() as conn:
            # Table creation check removed from here as it's handled on startup now
            
            # Check user quota
            result = conn.execute(text("""
                SELECT requests_remaining 
                FROM user_quotas 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            row = result.fetchone()
            
            if row is None:
                # User doesn't exist, create with 3 requests (free tier default for plan_v2)
                conn.execute(text("""
                    INSERT INTO user_quotas (user_id, requests_remaining, total_requests)
                    VALUES (:user_id, 3, 0)
                    ON CONFLICT (user_id) DO UPDATE SET
                        requests_remaining = 3
                        WHERE user_quotas.requests_remaining = 0
                """), {"user_id": user_id})
                conn.commit()
                return True  # New users get 3 free requests
            
            return row[0] > 0
    
    except Exception as e:
        logger.error(f"Error checking quota for user {user_id}: {str(e)}")
        # In case of error, allow request (fail open for MVP)
        return True


async def get_quota_info(user_id: str) -> dict:
    """
    Get detailed quota information for user
    
    Args:
        user_id: User ID to get quota info for
    
    Returns:
        Dictionary with remaining and total_requests, or None if user doesn't exist
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT requests_remaining, total_requests 
                FROM user_quotas 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            row = result.fetchone()
            
            if row is None:
                # User doesn't exist, create with default quota (3 requests for new users)
                conn.execute(text("""
                    INSERT INTO user_quotas (user_id, requests_remaining, total_requests)
                    VALUES (:user_id, 3, 0)
                    ON CONFLICT (user_id) DO NOTHING
                """), {"user_id": user_id})
                conn.commit()
                return {"remaining": 3, "total": 0}
            
            return {"remaining": row[0], "total": row[1]}
    
    except Exception as e:
        logger.error(f"Error getting quota info for user {user_id}: {str(e)}")
        return None


async def decrement_quota(user_id: str) -> bool:
    """
    Decrement user's quota atomically.
    
    Returns:
        True if quota was successfully decremented (user had quota).
        False if user had no quota remaining.
    """
    try:
        with engine.connect() as conn:
            # 1. Ensure user exists (Idempotent)
            conn.execute(text("""
                INSERT INTO user_quotas (user_id, requests_remaining, total_requests)
                VALUES (:user_id, 3, 0)
                ON CONFLICT (user_id) DO NOTHING
            """), {"user_id": user_id})
            
            # 2. Atomic Update: Decrement ONLY if > 0
            # We use returning to know the new state or row count to know if update happened
            result = conn.execute(text("""
                UPDATE user_quotas 
                SET 
                    requests_remaining = requests_remaining - 1,
                    total_requests = total_requests + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND requests_remaining > 0
            """), {"user_id": user_id})
            
            conn.commit()
            
            # rowcount will be 1 if update happened (quota > 0), 0 otherwise
            if result.rowcount > 0:
                logger.info(f"Decremented quota for user {user_id}")
                return True
            else:
                logger.warning(f"User {user_id} tried to decrement but has 0 quota")
                return False
    
    except Exception as e:
        logger.error(f"Error decrementing quota for user {user_id}: {str(e)}")
        # In case of DB error, we default to False to protect resources
        return False
