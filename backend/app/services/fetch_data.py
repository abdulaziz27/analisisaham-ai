"""
Data Fetching Service
Fetches OHLCV data from Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def get_ohlcv(ticker: str, days: int = 180) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Yahoo Finance
    
    Args:
        ticker: Stock ticker symbol (e.g., MDLA.JK for Jakarta, or MDLA)
        days: Number of days to fetch
    
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        # Add .JK suffix for Indonesian stocks if not present
        if not ticker.endswith('.JK') and not ticker.endswith('.ID'):
            ticker_symbol = f"{ticker}.JK"
        else:
            ticker_symbol = ticker
        
        # Fetch data
        stock = yf.Ticker(ticker_symbol)
        
        # Get historical data (minimum 6 months for plan_v2)
        period = "6mo" if days <= 180 else "1y" if days <= 365 else "max"
        df = stock.history(period=period)
        
        if df.empty:
            logger.warning(f"No data found for ticker: {ticker_symbol}")
            return None
        
        # Keep only requested days
        if len(df) > days:
            df = df.tail(days)
        
        # Reset index to make Date a column
        df.reset_index(inplace=True)
        
        # Ensure proper column names
        df.columns = df.columns.str.lower()
        
        logger.info(f"Successfully fetched {len(df)} days of data for {ticker_symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return None
