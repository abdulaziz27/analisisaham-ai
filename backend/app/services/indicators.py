"""
Technical Indicators Service
Computes technical analysis indicators
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from backend.app.models.schema import IndicatorsData

def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = df[column].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(df: pd.DataFrame, column: str = 'close') -> Dict[str, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema12 = calculate_ema(df, 12, column)
    ema26 = calculate_ema(df, 26, column)
    macd_line = ema12 - ema26
    signal_line = calculate_ema(pd.DataFrame({'close': macd_line}), 9, 'close')
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def find_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, Optional[float]]:
    """
    Find support and resistance levels using recent price action
    
    Support: Lowest low in recent period (last 50 days, or last 30% of data)
    Resistance: Highest high in recent period (last 50 days, or last 30% of data)
    """
    if df.empty or 'close' not in df.columns:
        return {'support': None, 'resistance': None}
    
    close = df['close']
    high = df['high'] if 'high' in df.columns else close
    low = df['low'] if 'low' in df.columns else close
    
    # Use recent data for more relevant levels (last 50 days or 30% of data, whichever is smaller)
    recent_window = min(window * 2, max(int(len(df) * 0.3), window))
    recent_df = df.tail(recent_window)
    
    # Support: lowest low in recent period
    support = float(recent_df['low'].min()) if 'low' in recent_df.columns else float(recent_df['close'].min())
    
    # Resistance: highest high in recent period
    resistance = float(recent_df['high'].max()) if 'high' in recent_df.columns else float(recent_df['close'].max())
    
    # If resistance is equal to current price or very close, use a more conservative approach
    current_price = float(close.iloc[-1])
    
    # If resistance is current price, look for previous resistance level
    if abs(resistance - current_price) < current_price * 0.01:  # Within 1%
        # Use second highest as resistance
        recent_highs = recent_df['high'].sort_values(ascending=False) if 'high' in recent_df.columns else recent_df['close'].sort_values(ascending=False)
        if len(recent_highs) > 1:
            resistance = float(recent_highs.iloc[1])
        else:
            resistance = current_price * 1.05  # 5% above current as default
    
    # Ensure support is below current price and resistance is above
    if support >= current_price:
        # Use recent low or EMA as fallback
        support = float(recent_df['low'].quantile(0.2)) if 'low' in recent_df.columns else current_price * 0.95
    
    if resistance <= current_price:
        resistance = current_price * 1.05  # Default 5% above
    
    return {
        'support': float(support) if not np.isnan(support) else None,
        'resistance': float(resistance) if not np.isnan(resistance) else None
    }

def compute_indicators(df: pd.DataFrame) -> IndicatorsData:
    """
    Compute all technical indicators from OHLCV data
    
    Args:
        df: DataFrame with OHLCV data (must have columns: open, high, low, close, volume)
    
    Returns:
        IndicatorsData object with computed indicators
    """
    if df.empty or 'close' not in df.columns:
        return IndicatorsData()
    
    # Get latest values
    latest = df.iloc[-1]
    current_price = float(latest['close'])
    
    # Calculate price change percent (daily change)
    if len(df) > 1:
        previous_close = float(df.iloc[-2]['close'])
        price_change_percent = ((current_price - previous_close) / previous_close) * 100
    else:
        price_change_percent = 0.0
    
    # Calculate period change (7d and 30d if available)
    price_change_7d = None
    price_change_30d = None
    if len(df) >= 7:
        price_7d_ago = float(df.iloc[-7]['close'])
        price_change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
    if len(df) >= 30:
        price_30d_ago = float(df.iloc[-30]['close'])
        price_change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
    
    # Calculate EMAs
    ema20_series = calculate_ema(df, 20)
    ema50_series = calculate_ema(df, 50)
    ema20 = float(ema20_series.iloc[-1]) if not ema20_series.empty else None
    ema50 = float(ema50_series.iloc[-1]) if not ema50_series.empty else None
    
    # Calculate RSI
    rsi_series = calculate_rsi(df, 14)
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not np.isnan(rsi_series.iloc[-1]) else None
    
    # Calculate MACD
    macd_data = calculate_macd(df)
    macd = float(macd_data['macd'].iloc[-1]) if not macd_data['macd'].empty else None
    macd_signal = float(macd_data['signal'].iloc[-1]) if not macd_data['signal'].empty else None
    macd_histogram = float(macd_data['histogram'].iloc[-1]) if not macd_data['histogram'].empty else None
    
    # Find Support/Resistance
    sr_levels = find_support_resistance(df, window=20)
    
    # Calculate average volume
    if 'volume' in df.columns:
        volume_avg = float(df['volume'].mean()) if not df['volume'].empty else None
    else:
        volume_avg = None
    
    return IndicatorsData(
        ema20=ema20,
        ema50=ema50,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        support=sr_levels['support'],
        resistance=sr_levels['resistance'],
        volume_avg=volume_avg,
        current_price=current_price,
        price_change_percent=price_change_percent,
        price_change_7d=price_change_7d,
        price_change_30d=price_change_30d
    )
