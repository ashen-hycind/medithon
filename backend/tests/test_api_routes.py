import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

class TestMeasurementsApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_extract_issues_api_endpoint(self):
        payload = {
            "text": "Had a throbbing headache, poor sleep, and drank two coffees before measuring"
        }
        response = self.client.post("/api/scan/extract-issues", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["raw_text"], payload["text"])
        self.assertIn("issues", data)
        self.assertIn("has_red_flags", data)

        tags = [issue["tag"] for issue in data["issues"]]
        self.assertIn("headache", tags)
        self.assertIn("caffeine_intake", tags)
        self.assertIn("poor_sleep", tags)
        self.assertFalse(data["has_red_flags"])

    def test_extract_issues_api_endpoint_red_flag(self):
        payload = {
            "text": "Feeling terrible with sudden chest tightness and blurred vision"
        }
        response = self.client.post("/api/scan/extract-issues", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["has_red_flags"])
        tags = [issue["tag"] for issue in data["issues"]]
        self.assertTrue("chest_pain" in tags or "vision_changes" in tags)

if __name__ == "__main__":
    unittest.main()
