
"""
LLM Service
Generates AI analysis reports using Google Gemini
"""
from google import genai
from google.genai import types
from backend.app.core.config import settings
import pandas as pd
from backend.app.models.schema import IndicatorsData
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

PROMPT_TEMPLATE = """You are StockAnalysisGPT, an expert technical analyst.

Your job: Provide a high-impact, executive summary of the stock based on the data.

STRICT CONSTRAINTS:
- **Max Length:** 250 words.
- **Style:** Bullet points, direct, professional Indonesian.
- **No Intro/Outro:** START DIRECTLY with the first bullet point. Do not say "Berikut ringkasan..." or "Semoga membantu".
- **No Fluff:** Do not explain what RSI or MACD is. Just interpret the values.
- **Structure:**
  1. **Tren & Struktur:** (Bullish/Bearish/Sideways, Key levels)
  2. **Indikator:** (Konfirmasi sinyal dari RSI/MACD/Volume)
  3. **Skenario:** (Jika breakout X, potensi ke Y. Jika breakdown A, support di B)
  4. **Kesimpulan:** (Strong Buy / Buy on Weakness / Wait / Sell)

INPUT DATA:
{data}
"""

def format_data_for_llm(ticker: str, df: pd.DataFrame, indicators: IndicatorsData) -> str:
    """
    Format OHLCV data and indicators into a concise string for LLM
    """
    latest = df.iloc[-1]
    period_days = len(df)
    price_range = {
        f'highest_{period_days}d': float(df['high'].max()),
        f'lowest_{period_days}d': float(df['low'].min()),
        'current': indicators.current_price,
        'change_percent': indicators.price_change_percent
    }
    volume_analysis = {
        'average': indicators.volume_avg,
        'current': float(latest.get('volume', 0)),
        'trend': 'naik' if len(df) > 10 and df['volume'].tail(5).mean() > df['volume'].head(5).mean() else 'turun'
    }
    data_summary = {
        'ticker': ticker,
        'period_days': len(df),
        'price': price_range,
        'price_changes': {
            'daily': indicators.price_change_percent,
            '7d': indicators.price_change_7d,
            '30d': indicators.price_change_30d
        },
        'indicators': {
            'EMA20': indicators.ema20,
            'EMA50': indicators.ema50,
            'RSI': indicators.rsi,
            'MACD': indicators.macd,
            'Support': indicators.support,
            'Resistance': indicators.resistance
        },
        'volume': volume_analysis
    }
    return json.dumps(data_summary, indent=2, ensure_ascii=False)


async def generate_report(ticker: str, df: pd.DataFrame, indicators: IndicatorsData) -> str:
    """
    Generate AI analysis report using Google Gemini with retry logic
    """
    formatted_data = format_data_for_llm(ticker, df, indicators)
    system_instruction = "You are a professional financial analyst specializing in Indonesian stock market analysis."
    user_prompt = PROMPT_TEMPLATE.format(data=formatted_data)
    full_prompt = f"{system_instruction}\n\n{user_prompt}"

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=2000
                )
            )
            report = response.text.strip()
            logger.info(f"Successfully generated report for {ticker}")
            return report
        except Exception as e:
            error_str = str(e)
            if ('503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower()) and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                logger.warning(f"Gemini API overloaded, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            logger.error(f"Error generating report for {ticker}: {error_str}")
            if '503' in error_str or 'overloaded' in error_str.lower():
                raise Exception("Model Gemini sedang sibuk. Silakan coba lagi dalam beberapa detik.")
            else:
                raise Exception(f"Gagal menghasilkan laporan AI: {error_str[:200]}")
    
    # This line is reached if all retries fail
    raise Exception("Model Gemini sedang sibuk setelah beberapa kali percobaan.")
