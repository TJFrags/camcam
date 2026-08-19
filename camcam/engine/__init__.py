"""
CamCam Engine Package
"""

from camcam.engine.base import (
    BaseCameraBackend,
    CameraStatus,
    CaptureResult,
    CameraConfig,
    CameraError,
    CameraNotConnectedError,
    CameraBusyError,
    AVAILABLE_SETTINGS,
    PRESETS,
)
from camcam.engine.mock_backend import MockCameraBackend
from camcam.engine.digicam_backend import DigiCamControlBackend
from camcam.engine.gphoto_backend import NativeGPhotoBackend, CLIGPhotoBackend
from camcam.engine.camera_manager import CameraManager
from camcam.engine.timelapse import TimelapseEngine

__all__ = [
    "BaseCameraBackend",
    "CameraStatus",
    "CaptureResult",
    "CameraConfig",
    "CameraError",
    "CameraNotConnectedError",
    "CameraBusyError",
    "AVAILABLE_SETTINGS",
    "PRESETS",
    "MockCameraBackend",
    "DigiCamControlBackend",
    "NativeGPhotoBackend",
    "CLIGPhotoBackend",
    "CameraManager",
    "TimelapseEngine",
]
