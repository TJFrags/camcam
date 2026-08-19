"""
Integration tests for FastAPI endpoints (Shutter Remote & Quick Settings Only).
"""

import unittest
from fastapi.testclient import TestClient
from camcam.web.app import app
from camcam.web.routes import camera_manager
from camcam.engine.mock_backend import MockCameraBackend


class TestAPI(unittest.TestCase):
    def setUp(self):
        backend = MockCameraBackend(simulate_latency=False)
        backend.connect()
        camera_manager.set_backend(backend)
        self.client = TestClient(app)

    def test_root_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_camera_status_api(self):
        response = self.client.get("/api/camera/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["connected"])
        self.assertIn("D3100", data["model"])

    def test_camera_settings_get_and_set(self):
        # GET settings
        response = self.client.get("/api/camera/settings")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("current", data)
        self.assertIn("available", data)

        # POST settings
        update_res = self.client.post("/api/camera/settings", json={"iso": "1600", "shutterspeed": "1/500"})
        self.assertEqual(update_res.status_code, 200)
        updated_data = update_res.json()
        self.assertEqual(updated_data["settings"]["current"]["iso"], "1600")

    def test_shutter_trigger_api(self):
        response = self.client.post("/api/shutter/trigger", json={"delay": 0.0})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("message", data)

    def test_burst_api(self):
        response = self.client.post("/api/shutter/burst", json={"count": 2, "delay_between": 0.05})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 2)

    def test_system_status_api(self):
        response = self.client.get("/api/system/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cpu_usage_percent", data)
        self.assertIn("memory_usage_percent", data)


if __name__ == "__main__":
    unittest.main()
