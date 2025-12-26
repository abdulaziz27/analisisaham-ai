"""
Chart Generator Service
Generates technical analysis charts using matplotlib
"""
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure tmp directory exists
TMP_DIR = Path("/tmp")
if not TMP_DIR.exists():
    TMP_DIR = Path("./tmp")
    TMP_DIR.mkdir(exist_ok=True)


def generate_chart(
    ticker: str,
    df: pd.DataFrame,
    ema20: Optional[float] = None,
    ema50: Optional[float] = None
) -> Optional[str]:
    """
    Generate price chart with EMA overlays
    
    Args:
        ticker: Stock ticker symbol
        df: DataFrame with OHLCV data (must have 'date' or datetime index and 'close')
        ema20: EMA20 value for the last period
        ema50: EMA50 value for the last period
    
    Returns:
        Path to saved chart file or None if error
    """
    try:
        if df.empty or 'close' not in df.columns:
            logger.error("Invalid DataFrame for chart generation")
            return None
        
        # Prepare date column
        df_copy = df.copy()
        
        if isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
        elif 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            dates = pd.to_datetime(df['Date'])
        else:
            # Create date range if no date available
            dates = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='D')
        
        # Get close prices
        close_prices = df['close'].values
        
        # Calculate EMA20 and EMA50 series for overlay
        if len(df_copy) >= 20:
            from backend.app.services.indicators import calculate_ema
            ema20_series = calculate_ema(df_copy, 20, 'close')
            ema50_series = calculate_ema(df_copy, 50, 'close') if len(df_copy) >= 50 else None
        else:
            ema20_series = None
            ema50_series = None
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot close price
        ax.plot(dates, close_prices, label='Harga Penutupan', color='#2E86AB', linewidth=2)
        
        # Highlight last 20 candles
        if len(df) >= 20:
            highlight_start = len(df) - 20
            ax.plot(
                dates[highlight_start:],
                close_prices[highlight_start:],
                color='#F24236',
                linewidth=2.5,
                alpha=0.8,
                label='20 Hari Terakhir'
            )
        
        # Plot EMA20
        if ema20_series is not None and not ema20_series.empty:
            ax.plot(
                dates,
                ema20_series.values,
                label='EMA20',
                color='#FF9500',
                linewidth=1.5,
                linestyle='--',
                alpha=0.8
            )
        
        # Plot EMA50
        if ema50_series is not None and not ema50_series.empty:
            ax.plot(
                dates,
                ema50_series.values,
                label='EMA50',
                color='#9D4EDD',
                linewidth=1.5,
                linestyle='--',
                alpha=0.8
            )
        
        # Formatting
        ax.set_title(f'Analisis Teknikal - {ticker}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Tanggal', fontsize=12)
        ax.set_ylabel('Harga (Rp)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle=':')
        
        # Format x-axis dates
        if isinstance(dates, pd.DatetimeIndex):
            fig.autofmt_xdate()
        
        # Set tight layout
        plt.tight_layout()
        
        # Save chart
        chart_filename = f"{ticker.replace('.', '_')}_chart.png"
        chart_path = TMP_DIR / chart_filename
        
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        logger.info(f"Chart saved to {chart_path}")
        return str(chart_path)
    
    except Exception as e:
        logger.error(f"Error generating chart for {ticker}: {str(e)}")
        if 'fig' in locals():
            plt.close(fig)
        return None
