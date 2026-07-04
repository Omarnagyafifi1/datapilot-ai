import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_standardized(self):
        # Verify custom exception handler maps correctly for non-existent routes
        response = self.client.get("/api/non-existent-route-for-testing")
        self.assertEqual(response.status_code, 404)
        json_data = response.json()
        self.assertIn("success", json_data)
        self.assertFalse(json_data["success"])
        self.assertIn("Not Found", json_data["message"])

if __name__ == "__main__":
    unittest.main()
