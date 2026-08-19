#!/usr/bin/env python3
"""
digiCamControl Installer Helper for Windows
===========================================
Automatically downloads and launches the official digiCamControl installer
to enable USB camera shutter control for Nikon D3100 on Windows.

Usage:
    python setup_windows.py
"""

import os
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

INSTALLER_URL = "https://downloads.sourceforge.net/project/digicamcontrol/digiCamControlsetup_2.1.7.0.exe"
LOCAL_INSTALLER = Path("./digiCamControl_setup.exe")


def log(msg: str):
    print(f"[*] {msg}")


def main():
    if platform.system() != "Windows":
        print("[!] This setup script is specifically for Windows.")
        print("    On Linux / Raspberry Pi, run: sudo apt install gphoto2 libgphoto2-dev")
        sys.exit(1)

    print("=" * 65)
    print("      NIKON D3100 WINDOWS DRIVER INSTALLER (digiCamControl)")
    print("=" * 65)
    print("\nTo trigger your Nikon D3100 over USB on Windows, we need the free")
    print("open-source digiCamControl driver (which includes CameraControlCmd.exe).\n")

    # Step 1: Check if already installed
    possible_paths = [
        Path(r"C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe"),
        Path(r"C:\Program Files\digiCamControl\CameraControlCmd.exe"),
        Path(os.path.expanduser(r"~\AppData\Local\digiCamControl\CameraControlCmd.exe")),
    ]
    for p in possible_paths:
        if p.is_file():
            print(f"[SUCCESS] digiCamControl is ALREADY installed at:\n  {p}")
            print("\nYou can take real photos right now with:")
            print("  python take_picture.py")
            return

    # Step 2: Download installer
    log("Downloading official digiCamControl installer (~50MB)...")
    log("Source: SourceForge / digiCamControl Official")

    def progress_bar(blocks, block_size, total_size):
        downloaded = blocks * block_size
        if total_size > 0:
            percent = min(100, int(downloaded * 100 / total_size))
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r    Downloading: {mb:.1f}MB / {total_mb:.1f}MB [{percent}%] ")
            sys.stdout.flush()

    try:
        # User-Agent header to avoid SourceForge blocking default urllib
        req = urllib.request.Request(
            INSTALLER_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req) as response, open(LOCAL_INSTALLER, 'wb') as out_file:
            total_size = int(response.info().get('Content-Length', -1))
            block_size = 65536
            downloaded = 0
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                out_file.write(buffer)
                downloaded += len(buffer)
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    sys.stdout.write(f"\r    Downloading: {downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB [{percent}%] ")
                    sys.stdout.flush()

        print("\n[SUCCESS] Download completed successfully!")
    except Exception as e:
        print(f"\n[!] Automatic download failed: {e}")
        print("\nPlease download the installer manually from:")
        print("  https://digicamcontrol.com/download")
        sys.exit(1)

    # Step 3: Run installer
    log("Launching installer...")
    log("Please click 'Next' / 'Install' in the installer window that appears.")
    try:
        subprocess.run([str(LOCAL_INSTALLER.resolve())], check=True)
    except Exception as e:
        log(f"Error launching installer: {e}")
        print(f"You can manually run: {LOCAL_INSTALLER.resolve()}")

    print("\n" + "=" * 65)
    print("Once installation completes, test taking a real photo with:")
    print("  python take_picture.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
