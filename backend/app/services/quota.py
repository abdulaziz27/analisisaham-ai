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
    """Ensure quota table exists and has necessary columns"""
    try:
        with engine.connect() as conn:
            # 1. Create table if not exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_quotas (
                    user_id VARCHAR(255) PRIMARY KEY,
                    requests_remaining INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            
            # 2. Add columns if not exist (Migration Logic)
            # Check if columns exist
            res = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_quotas';
            """))
            existing_columns = [row[0] for row in res.fetchall()]
            
            if 'username' not in existing_columns:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN username VARCHAR(255);"))
                logger.info("Added username column to user_quotas")
                
            if 'first_name' not in existing_columns:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN first_name VARCHAR(255);"))
                
            if 'last_name' not in existing_columns:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN last_name VARCHAR(255);"))
                
            if 'language_code' not in existing_columns:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN language_code VARCHAR(10);"))
                
            if 'is_premium' not in existing_columns:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;"))
                
            conn.commit()
            logger.info("Checked/Created user_quotas table schema")
    except Exception as e:
        logger.error(f"Error creating/migrating quota tables: {str(e)}")

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


async def get_quota_info(
    user_id: str, 
    username: str = None, 
    first_name: str = None,
    last_name: str = None,
    language_code: str = None,
    is_premium: bool = None
) -> dict:
    """
    Get detailed quota information for user and update user info
    """
    try:
        with engine.connect() as conn:
            # 1. Try to update existing user info
            if any([username, first_name, last_name, language_code, is_premium is not None]):
                conn.execute(text("""
                    UPDATE user_quotas 
                    SET 
                        username = COALESCE(:username, username),
                        first_name = COALESCE(:first_name, first_name),
                        last_name = COALESCE(:last_name, last_name),
                        language_code = COALESCE(:language_code, language_code),
                        is_premium = COALESCE(:is_premium, is_premium),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """), {
                    "user_id": user_id, 
                    "username": username, 
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code,
                    "is_premium": is_premium
                })
                conn.commit()

            # 2. Get info (or insert default if not exists)
            result = conn.execute(text("""
                SELECT requests_remaining, total_requests 
                FROM user_quotas 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            row = result.fetchone()
            
            if row is None:
                # User doesn't exist, create with default quota
                conn.execute(text("""
                    INSERT INTO user_quotas (user_id, requests_remaining, total_requests, username, first_name, last_name, language_code, is_premium)
                    VALUES (:user_id, 3, 0, :username, :first_name, :last_name, :language_code, :is_premium)
                    ON CONFLICT (user_id) DO NOTHING
                """), {
                    "user_id": user_id, 
                    "username": username, 
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code,
                    "is_premium": is_premium
                })
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
