"""
Camera Manager Singleton for Nikon D3100 (Shutter Trigger & Quick Settings Only)
"""

import platform
import threading
import time
from typing import Optional, List, Dict, Any

from camcam.engine.base import (
    BaseCameraBackend,
    CameraStatus,
    CaptureResult,
    CameraBusyError,
    PRESETS,
)
from camcam.engine.mock_backend import MockCameraBackend
from camcam.engine.digicam_backend import DigiCamControlBackend
from camcam.engine.gphoto_backend import NativeGPhotoBackend, CLIGPhotoBackend


class CameraManager:
    """Central manager coordinating camera hardware backends for shutter triggering and quick settings."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, force_mock: bool = False):
        if getattr(self, "_initialized", False):
            if force_mock and not isinstance(self.backend, MockCameraBackend):
                self.set_backend(MockCameraBackend())
            return

        self._camera_lock = threading.Lock()
        self.force_mock = force_mock
        self.backend: BaseCameraBackend = self._auto_select_backend()
        self._initialized = True

    def _auto_select_backend(self) -> BaseCameraBackend:
        if self.force_mock:
            return MockCameraBackend()

        # 1. Windows: digiCamControl
        if platform.system() == "Windows":
            dcc = DigiCamControlBackend()
            if dcc.connect():
                return dcc

        # 2. Linux / macOS: Native gphoto2
        native_gp = NativeGPhotoBackend()
        if native_gp.connect():
            return native_gp

        # 3. Linux / macOS: CLI gphoto2
        cli_gp = CLIGPhotoBackend()
        if cli_gp.connect():
            return cli_gp

        # 4. Fallback to Mock Backend for simulator
        mock = MockCameraBackend()
        mock.connect()
        return mock

    def set_backend(self, backend: BaseCameraBackend):
        with self._camera_lock:
            if hasattr(self, "backend") and self.backend:
                self.backend.disconnect()
            self.backend = backend

    def connect(self) -> bool:
        with self._camera_lock:
            return self.backend.connect()

    def is_connected(self) -> bool:
        return self.backend.is_connected()

    def get_status(self) -> CameraStatus:
        return self.backend.get_status()

    def get_config(self) -> Dict[str, Any]:
        return self.backend.get_config()

    def set_config(self, key: str, value: str) -> bool:
        return self.backend.set_config(key, str(value))

    def apply_preset(self, preset_name: str) -> bool:
        if preset_name in PRESETS:
            preset = PRESETS[preset_name]
            for k, v in preset.items():
                self.backend.set_config(k, str(v))
            return True
        return False

    def capture_image(
        self,
        delay: float = 0.0,
        settings: Optional[Dict[str, str]] = None
    ) -> CaptureResult:
        if not self._camera_lock.acquire(blocking=False):
            raise CameraBusyError("Camera is currently executing another capture operation.")

        try:
            if not self.backend.is_connected():
                self.backend.connect()

            if delay > 0:
                time.sleep(delay)

            return self.backend.capture(settings=settings)
        finally:
            self._camera_lock.release()

    def burst_capture(
        self,
        count: int = 3,
        delay_between: float = 0.2,
        settings: Optional[Dict[str, str]] = None
    ) -> List[CaptureResult]:
        if not self._camera_lock.acquire(blocking=False):
            raise CameraBusyError("Camera is currently executing another operation.")

        results = []
        try:
            if not self.backend.is_connected():
                self.backend.connect()

            for i in range(count):
                res = self.backend.capture(settings=settings)
                results.append(res)
                if i < count - 1 and delay_between > 0:
                    time.sleep(delay_between)
            return results
        finally:
            self._camera_lock.release()
