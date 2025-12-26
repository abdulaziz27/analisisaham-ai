
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.main import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_read_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Stock Analysis AI API", "version": "1.0.0"})

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    @patch("backend.app.routers.quota.get_quota_info", new_callable=AsyncMock)
    def test_check_quota_success(self, mock_get_quota):
        mock_get_quota.return_value = {"remaining": 5, "total": 10}
        
        response = self.client.get("/quota/check?user_id=123")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["remaining"], 5)

    @patch("backend.app.routers.quota.get_quota_info", new_callable=AsyncMock)
    def test_check_quota_empty(self, mock_get_quota):
        # Simulator user not found, returns None -> defaults to 3
        mock_get_quota.return_value = None
        
        response = self.client.get("/quota/check?user_id=999")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["remaining"], 3)

if __name__ == "__main__":
    unittest.main()
