"""
Windows DigiCamControl USB Camera Backend for Nikon D3100 (Ultra-Fast Instant Trigger)
"""

import os
import platform
import subprocess
import tempfile
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


class DigiCamControlBackend(BaseCameraBackend):
    name = "digiCamControl (Windows USB)"

    POSSIBLE_PATHS = [
        Path(r"C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe"),
        Path(r"C:\Program Files\digiCamControl\CameraControlCmd.exe"),
        Path(os.path.expanduser(r"~\AppData\Local\digiCamControl\CameraControlCmd.exe")),
    ]

    def __init__(self):
        self.cmd_path: Optional[Path] = None
        self._connected = False
        self._temp_dir = Path(tempfile.gettempdir()) / "camcam_tmp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._config = {
            "iso": "Auto",
            "shutterspeed": "1/125",
            "aperture": "5.6",
            "exposurecompensation": "0",
            "whitebalance": "Auto",
        }
        self._pending_settings = False
        self._find_executable()

    def _find_executable(self):
        for p in self.POSSIBLE_PATHS:
            if p.is_file():
                self.cmd_path = p
                break

    def connect(self) -> bool:
        if platform.system() != "Windows":
            return False

        if not self.cmd_path or not self.cmd_path.is_file():
            self._find_executable()

        if not self.cmd_path:
            return False

        self._connected = True
        return True

    def is_connected(self) -> bool:
        if not self.cmd_path:
            self._find_executable()
        return self.cmd_path is not None and self.cmd_path.is_file()

    def get_status(self) -> CameraStatus:
        connected = self.is_connected()
        return CameraStatus(
            connected=connected,
            model="Nikon D3100 (USB Tethered)",
            port="USB (PTP / digiCamControl)",
            battery_level=None,
            storage_target="Camera SD Card",
            ready=connected,
            backend_name=self.name,
            message="Ready (Instant Shutter Mode)" if connected else "digiCamControl not detected"
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
        if not self.is_connected() or not self.cmd_path:
            raise CameraNotConnectedError("digiCamControl CLI not available or camera not connected.")

        # Build command
        cmd = [str(self.cmd_path), "/folder", str(self._temp_dir)]

        # If settings were passed explicitly or changed
        if settings:
            for k, v in settings.items():
                if k in self._config:
                    self._config[k] = str(v)
            self._pending_settings = True

        if self._pending_settings:
            iso_val = self._config.get("iso")
            if iso_val and iso_val != "Auto":
                cmd.extend(["/iso", str(iso_val)])

            shutter_val = self._config.get("shutterspeed")
            if shutter_val:
                cmd.extend(["/shutter", str(shutter_val)])

            aperture_val = self._config.get("aperture")
            if aperture_val:
                cmd.extend(["/aperture", str(aperture_val)])

            ec_val = self._config.get("exposurecompensation")
            if ec_val and ec_val != "0":
                cmd.extend(["/ec", str(ec_val)])

            self._pending_settings = False

        # Direct trigger with no autofocus search for minimum actuation latency
        cmd.append("/capturenoaf")

        try:
            # Spawn the shutter trigger process
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Start background thread to clean up temp files once process completes
            def _cleanup_worker(p: subprocess.Popen, tmp_folder: Path):
                try:
                    p.wait(timeout=15)
                    for f in tmp_folder.iterdir():
                        if f.is_file():
                            try:
                                f.unlink(missing_ok=True)
                            except Exception:
                                pass
                except Exception:
                    pass

            threading.Thread(target=_cleanup_worker, args=(proc, self._temp_dir), daemon=True).start()

            return CaptureResult(
                success=True,
                message="Shutter triggered instantly! Photo stored on camera SD card.",
            )
        except Exception as e:
            return CaptureResult(
                success=False,
                error_message=str(e),
            )

    def disconnect(self):
        self._connected = False
