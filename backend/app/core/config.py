"""
Application Configuration
Loads environment variables and provides settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
import os
from pathlib import Path

# Get project root directory (assuming this file is in backend/app/core/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_NAME: str = "analisisaham-db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10
    
    # Google Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Midtrans (optional for MVP)
    MIDTRANS_SERVER_KEY: str = "SB-Mid-server-WTGzj-fdnz7U6SSuS3fhao7f"
    MIDTRANS_CLIENT_KEY: str = "SB-Mid-client-xo3JszBk1gen0AEn"
    MIDTRANS_IS_PRODUCTION: bool = False
    MIDTRANS_MERCHANT_ID: str = "G190200330"
    
    # Vercel
    VERCEL_URL: str = ""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    API_BASE_URL: str = "http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields like TELEGRAM_BOT_TOKEN, API_BASE_URL
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
