"""
Linux / Raspberry Pi 4 gphoto2 USB Camera Backend for Nikon D3100 (Instant Shutter & Quick Settings)
"""

import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from camcam.engine.base import (
    BaseCameraBackend,
    CameraStatus,
    CaptureResult,
    CameraNotConnectedError,
    AVAILABLE_SETTINGS,
    PRESETS,
)

try:
    import gphoto2 as gp
    GPHOTO_AVAILABLE = True
except Exception:
    GPHOTO_AVAILABLE = False


def unmount_gvfs_linux():
    """Unmount conflicting gvfs-gphoto2 daemons on Linux / Raspberry Pi."""
    if platform.system() == "Linux":
        try:
            subprocess.run(["pkill", "-9", "-f", "gvfsd-gphoto2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-9", "-f", "gvfs-gphoto2-volume-monitor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


class NativeGPhotoBackend(BaseCameraBackend):
    name = "python-gphoto2 (Native Linux/RPi)"

    def __init__(self):
        self.camera = None
        self.context = None
        self._connected = False
        self._config = {
            "iso": "Auto",
            "shutterspeed": "1/125",
            "aperture": "5.6",
            "exposurecompensation": "0",
            "whitebalance": "Auto",
            "delay": 0,
            "burst_count": 1,
        }

    def connect(self) -> bool:
        if not GPHOTO_AVAILABLE:
            return False

        unmount_gvfs_linux()
        try:
            self.context = gp.Context()
            self.camera = gp.Camera()
            self.camera.init(self.context)
            self._set_capture_target_card()
            self._connected = True
            return True
        except Exception:
            if self.camera:
                try:
                    self.camera.exit(self.context)
                except Exception:
                    pass
                self.camera = None
            self._connected = False
            return False

    def is_connected(self) -> bool:
        return self._connected and self.camera is not None

    def _set_capture_target_card(self):
        try:
            config = self.camera.get_config(self.context)
            try:
                widget = config.get_child_by_name("capturetarget")
                for i in range(widget.count_choices()):
                    choice = widget.get_choice(i)
                    if "card" in choice.lower() or "memory" in choice.lower() or choice == "1":
                        widget.set_value(choice)
                        self.camera.set_config(config, self.context)
                        break
            except Exception:
                pass
        except Exception:
            pass

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            connected=self.is_connected(),
            model="Nikon D3100 (Raspberry Pi USB)",
            port="USB (gphoto2 native)",
            battery_level=None,
            storage_target="Camera SD Card",
            ready=self.is_connected(),
            backend_name=self.name,
            message="Ready (RPi 4 High-Speed Shutter)" if self.is_connected() else "Camera not connected"
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
            if self.is_connected():
                self._apply_hardware_config(key, str(value))
            return True
        return False

    def _apply_hardware_config(self, key: str, value: str):
        if not self.camera:
            return
        try:
            config = self.camera.get_config(self.context)
            widget_names = {
                "iso": ["iso", "iso-speed"],
                "shutterspeed": ["shutterspeed", "shutterspeed2"],
                "aperture": ["f-number", "aperture"],
                "exposurecompensation": ["exposurecompensation"],
                "whitebalance": ["whitebalance"]
            }
            targets = widget_names.get(key, [key])
            for t in targets:
                try:
                    widget = config.get_child_by_name(t)
                    if widget:
                        widget.set_value(value)
                        self.camera.set_config(config, self.context)
                        break
                except Exception:
                    continue
        except Exception:
            pass

    def capture(self, settings: Optional[Dict[str, str]] = None) -> CaptureResult:
        if not self.is_connected():
            if not self.connect():
                raise CameraNotConnectedError("Native gphoto2 could not connect to camera.")

        if settings:
            for k, v in settings.items():
                self.set_config(k, v)

        try:
            # Trigger capture directly to SD card with zero computer download
            self.camera.trigger_capture(self.context)
            return CaptureResult(
                success=True,
                message="Shutter triggered instantly! Photo stored on camera SD card.",
            )
        except Exception as e:
            return CaptureResult(success=False, error_message=str(e))

    def disconnect(self):
        if self.camera:
            try:
                self.camera.exit(self.context)
            except Exception:
                pass
            self.camera = None
        self._connected = False


class CLIGPhotoBackend(BaseCameraBackend):
    name = "gphoto2 (CLI Linux/RPi)"

    def __init__(self):
        self.gphoto_path = shutil.which("gphoto2")
        self._connected = False
        self._config = {
            "iso": "Auto",
            "shutterspeed": "1/125",
            "aperture": "5.6",
            "exposurecompensation": "0",
            "whitebalance": "Auto",
            "delay": 0,
            "burst_count": 1,
        }
        self._pending_settings = False

    def connect(self) -> bool:
        if not self.gphoto_path:
            return False
        unmount_gvfs_linux()
        try:
            res = subprocess.run([self.gphoto_path, "--auto-detect"], capture_output=True, text=True, timeout=5)
            self._connected = "Nikon" in res.stdout or "D3100" in res.stdout or "Camera" in res.stdout or "USB" in res.stdout
            return self._connected
        except Exception:
            self._connected = False
            return False

    def is_connected(self) -> bool:
        return self.connect()

    def get_status(self) -> CameraStatus:
        connected = self.is_connected()
        return CameraStatus(
            connected=connected,
            model="Nikon D3100 (Raspberry Pi CLI)",
            port="USB (gphoto2 CLI)",
            ready=connected,
            storage_target="Camera SD Card",
            backend_name=self.name,
            message="Ready (RPi 4 Shutter Mode)" if connected else "Camera not detected"
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
            self._pending_settings = True
            return True
        return False

    def capture(self, settings: Optional[Dict[str, str]] = None) -> CaptureResult:
        if not self.gphoto_path:
            raise CameraNotConnectedError("gphoto2 CLI tool not found in PATH.")

        if settings:
            for k, v in settings.items():
                if k in self._config:
                    self._config[k] = str(v)
            self._pending_settings = True

        unmount_gvfs_linux()

        cmd = [self.gphoto_path, "--set-config", "capturetarget=1"]

        # Only apply hardware property changes when changed
        if self._pending_settings:
            if self._config.get("iso") and self._config["iso"] != "Auto":
                cmd.extend(["--set-config", f"iso={self._config['iso']}"])
            if self._config.get("shutterspeed"):
                cmd.extend(["--set-config", f"shutterspeed={self._config['shutterspeed']}"])
            if self._config.get("aperture"):
                cmd.extend(["--set-config", f"f-number={self._config['aperture']}"])
            if self._config.get("exposurecompensation") and self._config["exposurecompensation"] != "0":
                cmd.extend(["--set-config", f"exposurecompensation={self._config['exposurecompensation']}"])
            self._pending_settings = False

        cmd.append("--trigger-capture")

        try:
            # Fast non-blocking process spawn
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return CaptureResult(
                success=True,
                message="Shutter triggered instantly! Photo stored on camera SD card.",
            )
        except Exception as e:
            return CaptureResult(success=False, error_message=str(e))

    def disconnect(self):
        self._connected = False
