
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.indicators import calculate_rsi, calculate_macd, find_support_resistance
from backend.app.services.quota import decrement_quota

class TestIndicators(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame with 100 days of data
        dates = pd.date_range(start='2023-01-01', periods=100)
        # Create a trend + sine wave pattern
        prices = np.linspace(100, 200, 100) + 10 * np.sin(np.linspace(0, 10, 100))
        self.df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': prices + 5,
            'low': prices - 5,
            'close': prices,
            'volume': np.random.randint(1000, 5000, 100)
        })

    def test_rsi_calculation(self):
        rsi = calculate_rsi(self.df, period=14)
        # RSI should be between 0 and 100
        self.assertTrue(rsi.max() <= 100)
        self.assertTrue(rsi.min() >= 0)
        # Check last value is valid
        self.assertFalse(np.isnan(rsi.iloc[-1]))

    def test_macd_calculation(self):
        macd_data = calculate_macd(self.df)
        self.assertIn('macd', macd_data)
        self.assertIn('signal', macd_data)
        self.assertIn('histogram', macd_data)
        # Check dimensions match
        self.assertEqual(len(macd_data['macd']), 100)

    def test_support_resistance(self):
        levels = find_support_resistance(self.df)
        self.assertIsNotNone(levels['support'])
        self.assertIsNotNone(levels['resistance'])
        # Resistance should generally be higher than support
        self.assertTrue(levels['resistance'] >= levels['support'])

class TestQuotaService(unittest.IsolatedAsyncioTestCase):
    @patch('backend.app.services.quota.engine')
    async def test_decrement_quota_success(self, mock_engine):
        # Mock connection and execution
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock result for success (rowcount = 1)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        # The execute method is called twice (Insert, then Update)
        # We want the second call (Update) to return rowcount=1
        mock_conn.execute.side_effect = [MagicMock(), mock_result]
        
        success = await decrement_quota("user123")
        self.assertTrue(success)
        
    @patch('backend.app.services.quota.engine')
    async def test_decrement_quota_fail(self, mock_engine):
        # Mock connection
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock result for failure (rowcount = 0)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_conn.execute.side_effect = [MagicMock(), mock_result]
        
        success = await decrement_quota("user123")
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
