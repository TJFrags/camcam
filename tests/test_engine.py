"""
Unit tests for CameraManager and MockBackend (Shutter Only)
"""

import unittest

from camcam.engine.mock_backend import MockCameraBackend
from camcam.engine.camera_manager import CameraManager
from camcam.engine.base import CameraNotConnectedError


class TestEngine(unittest.TestCase):
    def test_mock_backend_lifecycle(self):
        backend = MockCameraBackend(simulate_latency=False)
        self.assertFalse(backend.is_connected())

        # Attempt capture while disconnected
        with self.assertRaises(CameraNotConnectedError):
            backend.capture()

        # Connect
        self.assertTrue(backend.connect())
        self.assertTrue(backend.is_connected())

        # Get status
        status = backend.get_status()
        self.assertTrue(status.connected)
        self.assertIn("D3100", status.model)

        # Capture
        result = backend.capture()
        self.assertTrue(result.success)
        self.assertIn("Actuation", result.message)

        # Settings
        cfg = backend.get_config()
        self.assertIn("iso", cfg["current"])
        self.assertTrue(backend.set_config("iso", "800"))
        self.assertEqual(backend.get_config()["current"]["iso"], "800")

        # Disconnect
        backend.disconnect()
        self.assertFalse(backend.is_connected())

    def test_camera_manager_singleton(self):
        cm = CameraManager(force_mock=True)
        self.assertTrue(cm.connect())
        status = cm.get_status()
        self.assertTrue(status.connected)

        # Trigger shutter
        res = cm.capture_image()
        self.assertTrue(res.success)

        # Burst capture
        burst = cm.burst_capture(count=2, delay_between=0.05)
        self.assertEqual(len(burst), 2)
        self.assertTrue(all(b.success for b in burst))

        # Quick Presets
        self.assertTrue(cm.apply_preset("Action"))
        self.assertEqual(cm.get_config()["current"]["iso"], "800")


if __name__ == "__main__":
    unittest.main()
