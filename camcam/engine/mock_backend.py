"""
Mock Camera Backend for Testing & Offline Simulation (Shutter Only)
"""

import time
from typing import Optional, Dict, Any

from camcam.engine.base import (
    BaseCameraBackend,
    CameraStatus,
    CaptureResult,
    CameraNotConnectedError,
    AVAILABLE_SETTINGS,
    PRESETS,
)


class MockCameraBackend(BaseCameraBackend):
    name = "Mock Simulator"

    def __init__(self, simulate_latency: bool = True):
        self._connected = False
        self._simulate_latency = simulate_latency
        self._shot_count = 0
        self._config = {
            "iso": "200",
            "shutterspeed": "1/125",
            "aperture": "5.6",
            "exposurecompensation": "0",
            "whitebalance": "Auto",
            "delay": 0,
            "burst_count": 1,
        }

    def connect(self) -> bool:
        if self._simulate_latency:
            time.sleep(0.1)
        self._connected = True
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            connected=self._connected,
            model="Nikon D3100 (Simulated USB)",
            port="USB (Mock)",
            battery_level=85,
            storage_target="Camera SD Card",
            ready=self._connected,
            backend_name=self.name,
            message="Simulator operational" if self._connected else "Not connected"
        )

    def get_config(self) -> Dict[str, Any]:
        return {
            "current": self._config.copy(),
            "available": AVAILABLE_SETTINGS,
            "presets": list(PRESETS.keys())
        }

    def set_config(self, key: str, value: str) -> bool:
        if key in self._config:
            self._config[key] = str(value)
            return True
        return False

    def capture(self, settings: Optional[Dict[str, str]] = None) -> CaptureResult:
        if not self._connected:
            raise CameraNotConnectedError("Camera is not connected. Call connect() first.")

        if settings:
            for k, v in settings.items():
                self.set_config(k, v)

        if self._simulate_latency:
            time.sleep(0.2)

        self._shot_count += 1
        return CaptureResult(
            success=True,
            message=f"Actuation #{self._shot_count} triggered on simulated camera SD card",
        )

    def disconnect(self):
        self._connected = False
