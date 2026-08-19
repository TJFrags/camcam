"""
CamCam Base Camera Engine Interfaces and Data Models (Shutter & Quick Settings Only)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime


class CameraError(Exception):
    """Base exception for camera errors."""
    pass


class CameraNotConnectedError(CameraError):
    """Raised when an operation requires an active camera connection."""
    pass


class CameraBusyError(CameraError):
    """Raised when the camera or USB bus is busy."""
    pass


@dataclass
class CameraStatus:
    connected: bool
    model: str = "Unknown"
    port: str = "USB"
    battery_level: Optional[int] = None
    storage_target: str = "Camera SD Card"
    ready: bool = True
    backend_name: str = "Base"
    message: str = ""


@dataclass
class CaptureResult:
    success: bool
    message: str = "Shutter triggered (Saved to camera SD card)"
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    error_message: Optional[str] = None


@dataclass
class CameraConfig:
    iso: str = "Auto"
    shutterspeed: str = "1/125"
    aperture: str = "5.6"
    exposurecompensation: str = "0"
    whitebalance: str = "Auto"
    focus_mode: str = "Manual"


# Available Quick Settings choices for Nikon D3100
AVAILABLE_SETTINGS = {
    "iso": ["Auto", "100", "200", "400", "800", "1600", "3200", "6400", "Hi-1"],
    "shutterspeed": [
        "1/4000", "1/2000", "1/1000", "1/500", "1/250", "1/125",
        "1/60", "1/30", "1/15", "1/8", "1/4", "1/2", "1s", "2s", "Bulb"
    ],
    "aperture": ["1.8", "2.8", "3.5", "4.0", "5.6", "8.0", "11", "16", "22"],
    "exposurecompensation": ["-3.0", "-2.0", "-1.5", "-1.0", "-0.5", "0", "+0.5", "+1.0", "+1.5", "+2.0", "+3.0"],
    "whitebalance": ["Auto", "Daylight", "Cloudy", "Shade", "Incandescent", "Fluorescent", "Flash"],
    "delay": [0, 2, 5, 10],
    "burst_count": [1, 2, 3, 5, 10]
}

# Quick Shooting Presets
PRESETS = {
    "Auto": {
        "iso": "Auto",
        "shutterspeed": "1/125",
        "aperture": "5.6",
        "exposurecompensation": "0",
        "whitebalance": "Auto"
    },
    "Action": {
        "iso": "800",
        "shutterspeed": "1/1000",
        "aperture": "4.0",
        "exposurecompensation": "0",
        "whitebalance": "Auto"
    },
    "Portrait": {
        "iso": "100",
        "shutterspeed": "1/250",
        "aperture": "2.8",
        "exposurecompensation": "+0.5",
        "whitebalance": "Daylight"
    },
    "Landscape": {
        "iso": "100",
        "shutterspeed": "1/60",
        "aperture": "11",
        "exposurecompensation": "0",
        "whitebalance": "Daylight"
    },
    "Night": {
        "iso": "1600",
        "shutterspeed": "1s",
        "aperture": "3.5",
        "exposurecompensation": "-0.5",
        "whitebalance": "Incandescent"
    },
    "Studio": {
        "iso": "100",
        "shutterspeed": "1/125",
        "aperture": "8.0",
        "exposurecompensation": "0",
        "whitebalance": "Flash"
    }
}


class BaseCameraBackend:
    name: str = "Base"

    def connect(self) -> bool:
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError

    def get_status(self) -> CameraStatus:
        raise NotImplementedError

    def get_config(self) -> Dict[str, Any]:
        raise NotImplementedError

    def set_config(self, key: str, value: str) -> bool:
        raise NotImplementedError

    def capture(self, settings: Optional[Dict[str, str]] = None) -> CaptureResult:
        raise NotImplementedError

    def disconnect(self):
        pass
