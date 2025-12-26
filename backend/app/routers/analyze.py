"""
Analysis Router
Handles stock analysis requests
"""
from fastapi import APIRouter, HTTPException, Depends
from backend.app.models.schema import AnalyzeRequest, AnalyzeResponse
from backend.app.services.fetch_data import get_ohlcv
from backend.app.services.indicators import compute_indicators
from backend.app.services.llm import generate_report
from backend.app.services.quota import check_quota, decrement_quota
from backend.app.services.chart import generate_chart

router = APIRouter()


@router.post(
    "/analyze", 
    response_model=AnalyzeResponse,
    summary="Menganalisis Saham",
    responses={
        200: {"description": "Analisis berhasil dihasilkan"},
        404: {"description": "Ticker tidak ditemukan atau data kosong"},
        500: {"description": "Kegagalan internal server atau API AI"}
    }
)
async def analyze_stock(
    request: AnalyzeRequest
):
    """
    Melakukan analisis mendalam terhadap sebuah ticker saham:
    - Mengambil data histori 6 bulan (OHLCV).
    - Menghitung indikator (EMA, RSI, MACD, Support/Resistance).
    - Membuat visualisasi chart.
    - Menghasilkan narasi analisis menggunakan Google Gemini AI.
    """
    try:
        # Note: Quota check should be done by Telegram bot before calling this endpoint
        # This endpoint assumes quota has already been checked and decremented
        
        # Fetch OHLCV data (6 months for plan_v2)
        df = await get_ohlcv(request.ticker, days=180)
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Data untuk ticker {request.ticker} tidak ditemukan"
            )
        
        # Compute indicators
        indicators = compute_indicators(df)
        
        # Generate chart
        chart_path = generate_chart(
            request.ticker,
            df,
            ema20=indicators.ema20,
            ema50=indicators.ema50
        )
        
        # Generate AI report (full report for plan_v2)
        ai_report = await generate_report(request.ticker, df, indicators)
        
        return AnalyzeResponse(
            ticker=request.ticker,
            ohlcv_days=180,
            indicators=indicators,
            ai_report=ai_report,
            chart_path=chart_path
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saat menganalisis: {str(e)}"
        )
