"""
FastAPI Application Entry Point
Main application configuration and CORS setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.routers import analyze, quota, payment
from backend.app.core.config import settings
from backend.app.core.http_client import close_http_client
from backend.app.core.rate_limit import RateLimitMiddleware
from backend.app.models.database import init_db
# Initialize logging
import backend.app.core.logging_config
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting application...")
    # Initialize database tables (only in development)
    # In production, use Alembic migrations
    if settings.ENVIRONMENT == "development":
        try:
            init_db()
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_http_client()


app = FastAPI(
    title="Stock Analysis AI API",
    description="""
    ## API untuk Analisis Saham Berbasis AI
    API ini menyediakan layanan analisis teknikal dan laporan cerdas menggunakan Google Gemini.
    
    ### Fitur Utama:
    * **Analyze**: Mengambil data OHLCV, menghitung indikator teknikal, dan menghasilkan laporan AI.
    * **Quota**: Manajemen kuota pengguna untuk membatasi penggunaan API.
    * **Payment**: Integrasi pembayaran Midtrans untuk top-up kuota.
    """,
    version="1.0.0",
    contact={
        "name": "Support Team",
        "url": "http://example.com/support",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# Rate Limiting (before CORS)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router, prefix="/api", tags=["analysis"])
app.include_router(quota.router, prefix="/quota", tags=["quota"])
app.include_router(payment.router, prefix="/payment", tags=["payment"])


@app.get("/")
async def root():
    return {"message": "Stock Analysis AI API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
