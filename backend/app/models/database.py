"""
Database Models and Session Management
SQLAlchemy ORM models and dependency injection for database sessions
"""
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from backend.app.core.config import settings
from typing import Generator
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserQuota(Base):
    """User quota model"""
    __tablename__ = "user_quotas"
    
    user_id = Column(String(255), primary_key=True, index=True)
    requests_remaining = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_premium = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PaymentTransaction(Base):
    """Payment transaction model"""
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    order_id = Column(String(255), unique=True, nullable=False, index=True)
    plan_id = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    payment_type = Column(String(50), nullable=True)
    transaction_time = Column(DateTime(timezone=True), nullable=True)
    settlement_time = Column(DateTime(timezone=True), nullable=True)
    midtrans_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# Database engine and session factory
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_MIN,
    max_overflow=settings.DB_POOL_MAX - settings.DB_POOL_MIN,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for database sessions.
    Ensures proper session lifecycle management.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables (for development/testing)"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
