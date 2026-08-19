"""
CamCam Unified Camera Engine for Nikon D3100 (Shutter Trigger & Quick Settings Only)
"""

from typing import Optional, List, Dict
from camcam.engine.camera_manager import CameraManager
from camcam.engine.base import CaptureResult, CameraStatus, PRESETS


class CameraEngine:
    """High-level Python controller for triggering Nikon D3100 shutter."""

    def __init__(self, backend_type: str = "auto", **kwargs):
        self.cm = CameraManager(force_mock=(backend_type == "mock"))

    def snap(self, settings: Optional[Dict[str, str]] = None) -> CaptureResult:
        """Trigger a single shot directly to the camera's SD card."""
        return self.cm.capture_image(settings=settings)

    def burst(self, count: int = 3, interval: float = 0.2, settings: Optional[Dict[str, str]] = None) -> List[CaptureResult]:
        """Trigger a rapid burst of photos."""
        return self.cm.burst_capture(count=count, delay_between=interval, settings=settings)

    def set_setting(self, key: str, value: str) -> bool:
        """Update a quick setting (iso, shutterspeed, aperture, etc.)."""
        return self.cm.set_config(key, value)

    def apply_preset(self, preset_name: str) -> bool:
        """Apply a shooting preset (Action, Portrait, Landscape, Night, Studio, Auto)."""
        return self.cm.apply_preset(preset_name)

    def get_status(self) -> CameraStatus:
        """Get camera connection status."""
        return self.cm.get_status()

    def close(self):
        """Release camera connection."""
        pass
