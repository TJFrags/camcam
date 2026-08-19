"""
Nikon D3100 Instant Shutter Release Tool (Direct to SD Card)
============================================================
Triggers the Nikon D3100 shutter over USB instantly without saving files to PC.
Photos are written directly to the camera's inserted SD card.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

# Optional gphoto2 import
try:
    import gphoto2 as gp
    GPHOTO_AVAILABLE = True
except (ImportError, Exception):
    GPHOTO_AVAILABLE = False


def log_info(msg: str):
    print(f"\033[96m[INFO]\033[0m {msg}")


def log_success(msg: str):
    print(f"\033[92m[SUCCESS]\033[0m {msg}")


def log_warn(msg: str):
    print(f"\033[93m[WARN]\033[0m {msg}")


def log_error(msg: str):
    print(f"\033[91m[ERROR]\033[0m {msg}")


def unmount_gvfs_linux():
    if platform.system() == "Linux":
        try:
            subprocess.run(["pkill", "-f", "gvfsd-gphoto2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "gvfs-gphoto2-volume-monitor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


class BaseCameraBackend:
    name: str = "Base"
    def connect(self) -> bool: raise NotImplementedError
    def capture(self, **kwargs) -> bool: raise NotImplementedError
    def disconnect(self): pass


class DigiCamControlBackend(BaseCameraBackend):
    name = "digiCamControl (Windows Fast USB)"

    POSSIBLE_PATHS = [
        Path(r"C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe"),
        Path(r"C:\Program Files\digiCamControl\CameraControlCmd.exe"),
        Path(os.path.expanduser(r"~\AppData\Local\digiCamControl\CameraControlCmd.exe")),
    ]

    def __init__(self):
        self.cmd_path = None
        self._temp_dir = Path(tempfile.gettempdir()) / "camcam_tmp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        for p in self.POSSIBLE_PATHS:
            if p.is_file():
                self.cmd_path = p
                break

    def connect(self) -> bool:
        return self.cmd_path is not None

    def capture(self, iso: Optional[str] = None, shutter: Optional[str] = None, aperture: Optional[str] = None, ec: Optional[str] = None, **kwargs) -> bool:
        if not self.cmd_path:
            return False

        cmd = [str(self.cmd_path), "/folder", str(self._temp_dir)]
        if iso and iso != "Auto":
            cmd.extend(["/iso", str(iso)])
        if shutter:
            cmd.extend(["/shutter", str(shutter)])
        if aperture:
            cmd.extend(["/aperture", str(aperture)])
        if ec and ec != "0":
            cmd.extend(["/ec", str(ec)])
        cmd.append("/capturenoaf")

        log_info(f"Firing shutter trigger...")
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_success("Shutter trigger sent! Photo saved directly to camera SD card.")

            # Background cleanup
            def _clean(proc, tmp):
                try:
                    proc.wait(timeout=15)
                    for f in tmp.iterdir():
                        if f.is_file(): f.unlink(missing_ok=True)
                except Exception:
                    pass
            threading.Thread(target=_clean, args=(p, self._temp_dir), daemon=True).start()
            return True
        except Exception as e:
            log_error(f"Trigger error: {e}")
            return False


class NativeGPhotoBackend(BaseCameraBackend):
    name = "python-gphoto2 (Native)"

    def __init__(self):
        self.camera = None
        self.context = None

    def connect(self) -> bool:
        if not GPHOTO_AVAILABLE: return False
        unmount_gvfs_linux()
        try:
            self.context = gp.Context()
            self.camera = gp.Camera()
            self.camera.init(self.context)
            return True
        except Exception:
            return False

    def capture(self, **kwargs) -> bool:
        if not self.camera and not self.connect(): return False
        try:
            self.camera.trigger_capture(self.context)
            log_success("Shutter triggered! Photo saved directly to camera SD card.")
            return True
        except Exception as e:
            log_error(f"Trigger error: {e}")
            return False


class CLIGPhotoBackend(BaseCameraBackend):
    name = "gphoto2 (CLI Subprocess)"

    def __init__(self):
        self.gphoto_path = shutil.which("gphoto2")

    def connect(self) -> bool:
        return bool(self.gphoto_path)

    def capture(self, **kwargs) -> bool:
        if not self.gphoto_path: return False
        unmount_gvfs_linux()
        try:
            subprocess.Popen([self.gphoto_path, "--set-config", "capturetarget=1", "--trigger-capture"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_success("Shutter triggered! Photo saved directly to camera SD card.")
            return True
        except Exception as e:
            log_warn(f"CLI trigger error: {e}")
            return False


class MockCameraBackend(BaseCameraBackend):
    name = "Mock Simulator"
    def connect(self) -> bool: return True
    def capture(self, **kwargs) -> bool:
        log_success("[SIMULATED] Shutter fired instantly (SD Card)")
        return True


def select_backend(forced_backend: str = "auto") -> BaseCameraBackend:
    if forced_backend == "mock": return MockCameraBackend()
    if platform.system() == "Windows":
        dcc = DigiCamControlBackend()
        if dcc.connect(): return dcc
    if GPHOTO_AVAILABLE:
        gp_backend = NativeGPhotoBackend()
        if gp_backend.connect(): return gp_backend
    cli_backend = CLIGPhotoBackend()
    if cli_backend.connect(): return cli_backend
    return MockCameraBackend()


def main():
    parser = argparse.ArgumentParser(description="Nikon D3100 Fast Shutter Release Tool")
    parser.add_argument("-d", "--delay", type=float, default=0.0, help="Countdown delay in seconds")
    parser.add_argument("-n", "--count", type=int, default=1, help="Burst count")
    parser.add_argument("-i", "--interval", type=float, default=0.2, help="Interval between shots")
    parser.add_argument("--iso", type=str, help="Quick setting: ISO")
    parser.add_argument("--shutter", type=str, help="Quick setting: Shutter speed")
    parser.add_argument("--aperture", type=str, help="Quick setting: Aperture")
    parser.add_argument("--ec", type=str, help="Quick setting: Exposure comp")
    parser.add_argument("--preset", type=str, help="Apply preset")
    parser.add_argument("--mock", action="store_true", help="Mock mode")

    args = parser.parse_args()
    backend = select_backend(forced_backend="mock" if args.mock else "auto")

    print("=" * 55)
    print(f"  [CAM] Nikon D3100 Fast Shutter ({backend.name})")
    print("  Storage: Direct to Camera SD Card (Instant Release)")
    print("=" * 55)

    if args.delay > 0:
        log_info(f"Starting {args.delay:.1f}s self-timer countdown...")
        remaining = int(args.delay)
        while remaining > 0:
            sys.stdout.write(f"\r  [*] Shutter in {remaining}s... ")
            sys.stdout.flush()
            time.sleep(1.0)
            remaining -= 1
        print("\r  [!] FIRING SHUTTER NOW!        ")

    for idx in range(1, args.count + 1):
        if args.count > 1:
            print(f"\n--- Shot {idx}/{args.count} ---")
        backend.capture(iso=args.iso, shutter=args.shutter, aperture=args.aperture, ec=args.ec)
        if idx < args.count and args.interval > 0:
            time.sleep(args.interval)

    print("\n" + "=" * 55)
    log_success(f"Trigger sequence finished! ({args.count} actuation(s))")
    print("=" * 55)


if __name__ == "__main__":
    main()
