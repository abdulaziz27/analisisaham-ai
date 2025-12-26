"""
FastAPI Application Entry Point
Main application configuration and CORS setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import analyze, quota, payment
from backend.app.core.config import settings
# Initialize logging
import backend.app.core.logging_config

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
