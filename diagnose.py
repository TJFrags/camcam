#!/usr/bin/env python3
"""
Nikon D3100 Diagnostic & Troubleshooting Utility
================================================
Checks system environment, USB connections, OS locks, camera communication,
and gives exact troubleshooting advice for Nikon D3100 tethered control.

Usage:
    python diagnose.py
    python diagnose.py --mock
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_status(label: str, status: bool, details: str = ""):
    icon = f"{Colors.OKGREEN}[PASS]{Colors.ENDC}" if status else f"{Colors.FAIL}[FAIL]{Colors.ENDC}"
    print(f"  {icon} {label:<32} {details}")


def print_warn(label: str, details: str = ""):
    print(f"  {Colors.WARNING}[WARN]{Colors.ENDC} {label:<32} {details}")


def print_info(label: str, details: str = ""):
    print(f"  {Colors.OKCYAN}[INFO]{Colors.ENDC} {label:<32} {details}")


def main():
    parser = argparse.ArgumentParser(description="Nikon D3100 Diagnostic Tool")
    parser.add_argument("--mock", action="store_true", help="Simulate diagnostic run")
    args = parser.parse_args()

    print("=" * 65)
    print("      [DIAG] NIKON D3100 SYSTEM & CONNECTION DIAGNOSTICS")
    print("=" * 65)

    os_type = platform.system()
    print_info("Operating System", f"{os_type} {platform.release()} ({platform.machine()})")
    print_info("Python Version", f"{sys.version.split()[0]} ({sys.executable})")

    # 1. Check Python Libraries
    print("\n--- 1. Python Dependencies ---")
    
    try:
        import PIL
        print_status("Pillow (Image Processing)", True, f"v{PIL.__version__}")
    except ImportError:
        print_warn("Pillow (Image Processing)", "Not installed (Optional for thumbnail/simulator)")

    try:
        import gphoto2 as gp
        print_status("python-gphoto2 (Native)", True, f"v{gp.__version__}")
    except Exception as e:
        if os_type == "Windows":
            print_info("python-gphoto2 (Native)", "Not compiled for Windows (digiCamControl will be used)")
        else:
            print_warn("python-gphoto2 (Native)", f"Not installed ({e}). Use: pip install gphoto2")

    # 2. Check System CLI Tools
    print("\n--- 2. System Software & Drivers ---")

    if os_type == "Linux":
        gphoto_path = shutil.which("gphoto2")
        print_status("gphoto2 CLI Tool", bool(gphoto_path), gphoto_path or "Install with: sudo apt install gphoto2")

        # Check for gvfs locks
        try:
            gvfs_check = subprocess.run(["pgrep", "-f", "gvfsd-gphoto2"], capture_output=True, text=True)
            if gvfs_check.returncode == 0:
                print_warn("Desktop USB Lock (gvfs)", "gvfsd-gphoto2 is active! Run: sudo pkill -f gvfsd-gphoto2")
            else:
                print_status("Desktop USB Locks", True, "No conflicting gvfs process detected")
        except Exception:
            pass

    elif os_type == "Windows":
        dcc_paths = [
            r"C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe",
            r"C:\Program Files\digiCamControl\CameraControlCmd.exe",
            os.path.expanduser(r"~\AppData\Local\digiCamControl\CameraControlCmd.exe"),
        ]
        found_dcc = None
        for p in dcc_paths:
            if os.path.isfile(p):
                found_dcc = p
                break
        print_status("digiCamControl CLI", bool(found_dcc), found_dcc or "Install digiCamControl from digicamcontrol.com")

    # 3. Check USB Connection to Nikon D3100
    print("\n--- 3. Camera USB Connectivity ---")

    if args.mock:
        print_status("Nikon D3100 USB", True, "[SIMULATED] Nikon D3100 (VID: 04b0, PID: 0427) Detected")
        print_status("PTP Shutter Response", True, "[SIMULATED] Camera acknowledged trigger command")
    else:
        # Check native gphoto auto-detect if available
        camera_found = False
        if os_type == "Linux":
            gphoto_path = shutil.which("gphoto2")
            if gphoto_path:
                try:
                    res = subprocess.run([gphoto_path, "--auto-detect"], capture_output=True, text=True, timeout=5)
                    if "Nikon" in res.stdout or "D3100" in res.stdout:
                        camera_found = True
                        print_status("Nikon D3100 USB", True, "Camera detected by gphoto2")
                    else:
                        print_status("Nikon D3100 USB", False, "No camera reported in 'gphoto2 --auto-detect'")
                except Exception as e:
                    print_status("Nikon D3100 USB", False, str(e))
        elif os_type == "Windows":
            print_info("USB Detection", "Ensure camera is turned ON and connected via Mini-USB cable.")

    # 4. Critical Hardware Checklist & Recommendations
    print("\n" + "=" * 65)
    print("      [*] NIKON D3100 CRITICAL SETTINGS CHECKLIST")
    print("=" * 65)
    print("""
  1. [FOCUS SWITCH]:
     Switch the lens focus toggle to 'M' (Manual Focus).
     *Reason: In Autofocus (A/M) mode, the camera will refuse to fire
     the shutter if it cannot lock focus on a subject.*

  2. [MODE DIAL]:
     Turn top dial to 'M' (Manual), 'A' (Aperture), 'S', or 'P'.
     *Reason: 'AUTO' and Scene modes disable USB PTP commands.*

  3. [SD CARD]:
     Ensure an SD card is inserted.
     *Reason: Nikon D3100 has no SDRAM buffer for direct computer storage.*

  4. [BATTERY]:
     Ensure battery has sufficient charge (>30%).

  5. [USB LOCKS (Linux / Raspberry Pi)]:
     If you get 'Device or resource busy', run:
     $ sudo pkill -f gvfsd-gphoto2
""")
    print("=" * 65)


if __name__ == "__main__":
    main()
