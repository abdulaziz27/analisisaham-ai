"""
Pydantic Schemas
Request and response models
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., description="Simbol ticker saham (contoh: BBCA, ASII, TLKM)", example="BBCA")
    user_id: str = Field(..., description="ID Telegram User untuk pelacakan kuota", example="12345678")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "BBCA",
                "user_id": "12345678"
            }
        }
    }


class IndicatorsData(BaseModel):
    ema20: Optional[float] = Field(None, example=9500.5)
    ema50: Optional[float] = Field(None, example=9300.0)
    rsi: Optional[float] = Field(None, example=65.2)
    macd: Optional[float] = Field(None, example=15.3)
    macd_signal: Optional[float] = Field(None, example=10.1)
    macd_histogram: Optional[float] = Field(None, example=5.2)
    support: Optional[float] = Field(None, example=9000.0)
    resistance: Optional[float] = Field(None, example=10000.0)
    volume_avg: Optional[float] = Field(None, example=1500000)
    current_price: Optional[float] = Field(None, example=9625.0)
    price_change_percent: Optional[float] = Field(None, example=1.5)
    price_change_7d: Optional[float] = Field(None, example=3.2)
    price_change_30d: Optional[float] = Field(None, example=-1.5)


class AnalyzeResponse(BaseModel):
    ticker: str = Field(..., example="BBCA")
    ohlcv_days: int = Field(..., example=180)
    indicators: IndicatorsData
    ai_report: str = Field(..., description="Laporan analisis teks dari Gemini AI")
    chart_path: Optional[str] = Field(None, example="/tmp/BBCA_chart.png")
