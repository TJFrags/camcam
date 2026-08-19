"""
CamCam Unified Command Line Interface (Shutter Remote & Quick Settings Only)
"""

import argparse
import uvicorn

from camcam.engine.camera_manager import CameraManager
from camcam.engine.mock_backend import MockCameraBackend
from camcam.engine.base import AVAILABLE_SETTINGS, PRESETS


def get_local_ip() -> str:
    """Detect local LAN IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def cmd_serve(args):
    """Launch FastAPI Web Interface and Quick Settings Dashboard."""
    cm = CameraManager(force_mock=args.mock)
    if args.mock:
        cm.set_backend(MockCameraBackend())

    lan_ip = get_local_ip()

    print("=" * 65)
    print("      [CAMCAM] NIKON D3100 QUICK SETTINGS WEB REMOTE")
    print("=" * 65)
    print(f"  Local Browser : http://localhost:{args.port}  (or http://127.0.0.1:{args.port})")
    print(f"  Phone / Tablet: http://{lan_ip}:{args.port}")
    print(f"  Camera Mode   : {'Offline Mock Simulator' if args.mock else 'Wired USB Tethered (D3100)'}")
    print("  Storage Mode  : 100% Direct to Camera SD Card (0 bytes stored on PC)")
    print("=" * 65)
    print("  Click or open http://localhost:8000 in your browser!\n")

    uvicorn.run("camcam.web.app:app", host=args.host, port=args.port, reload=args.reload)


def cmd_shutter(args):
    """Trigger one or more shots directly to the camera's SD card."""
    cm = CameraManager(force_mock=args.mock)
    if args.mock:
        cm.set_backend(MockCameraBackend())

    if args.preset:
        preset_name = next((p for p in PRESETS if p.lower() == args.preset.lower()), args.preset)
        cm.apply_preset(preset_name)
        print(f"[*] Applied Preset: {preset_name}")

    if args.iso:
        cm.set_config("iso", args.iso)
    if args.shutter:
        cm.set_config("shutterspeed", args.shutter)
    if args.aperture:
        cm.set_config("aperture", args.aperture)
    if args.ec:
        cm.set_config("exposurecompensation", args.ec)

    cfg = cm.get_config()["current"]
    print("=" * 55)
    print(f"  Shutter Trigger | Settings: ISO {cfg['iso']} | {cfg['shutterspeed']} | f/{cfg['aperture']}")
    print("=" * 55)

    if args.count > 1:
        print(f"[*] Triggering burst of {args.count} shots...")
        results = cm.burst_capture(count=args.count, delay_between=args.interval or 0.2)
        saved = [r for r in results if r.success]
        print(f"[SUCCESS] Fired {len(saved)}/{args.count} shots. Saved directly to camera SD card.")
    else:
        print("[*] Triggering shutter...")
        res = cm.capture_image(delay=args.delay)
        if res.success:
            print(f"[SUCCESS] {res.message}")
        else:
            print(f"[ERROR] Trigger failed: {res.error_message}")


def cmd_timelapse(args):
    """Run an automated intervalometer sequence from the CLI."""
    from camcam.engine.timelapse import TimelapseEngine
    import time

    cm = CameraManager(force_mock=args.mock)
    if args.mock:
        cm.set_backend(MockCameraBackend())

    engine = TimelapseEngine(cm)

    print("=" * 60)
    print("      TIMELAPSE INTERVALOMETER ACTIVE")
    print(f"      Interval: {args.interval}s | Target: {'Continuous' if args.count == 0 else f'{args.count} frames'}")
    print("      Storage: Camera SD Card")
    print("      Press Ctrl+C to stop.")
    print("=" * 60)

    engine.add_on_shot_callback(lambda res: print(f"  [Shutter Fired] Actuation recorded on camera SD card"))
    engine.start(interval_seconds=args.interval, total_shots=args.count)

    try:
        while engine.get_status().active:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Stopping timelapse...")
    finally:
        engine.stop()
        st = engine.get_status()
        print(f"\n[DONE] Finished! Total frames recorded on SD card: {st.shots_taken}")


def cmd_settings(args):
    """View or test camera Quick Settings and Presets."""
    cm = CameraManager(force_mock=args.mock)
    cfg = cm.get_config()

    print("=" * 60)
    print("      [SETTINGS] NIKON D3100 QUICK SETTINGS")
    print("=" * 60)
    print("\n--- Current Settings ---")
    for k, v in cfg["current"].items():
        print(f"  {k:<22}: {v}")

    print("\n--- Available Choices ---")
    for k, v in AVAILABLE_SETTINGS.items():
        print(f"  {k:<22}: {', '.join(str(x) for x in v)}")

    print("\n--- Available Presets ---")
    for p, vals in PRESETS.items():
        print(f"  * {p:<18}: {vals}")
    print("=" * 60)


def cmd_info(args):
    """Display connection and system status."""
    cm = CameraManager(force_mock=args.mock)
    st = cm.get_status()
    print("=" * 60)
    print("      [INFO] CAMERA CONNECTION INFO")
    print("=" * 60)
    print(f"  Connected      : {st.connected}")
    print(f"  Model          : {st.model}")
    print(f"  Port           : {st.port}")
    print(f"  Driver Backend : {st.backend_name}")
    print(f"  Storage Target : {st.storage_target}")
    print(f"  Message        : {st.message}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="CamCam - Nikon D3100 Shutter & Quick Settings Suite")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start FastAPI Web Interface")
    p_serve.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    p_serve.add_argument("--mock", action="store_true", help="Run with simulated mock camera backend")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")

    # shutter
    p_shutter = subparsers.add_parser("shutter", help="Trigger camera shutter")
    p_shutter.add_argument("-d", "--delay", type=float, default=0.0, help="Self-timer delay in seconds")
    p_shutter.add_argument("-n", "--count", type=int, default=1, help="Burst count")
    p_shutter.add_argument("-i", "--interval", type=float, default=0.2, help="Interval between burst shots")
    p_shutter.add_argument("--iso", type=str, help="Set ISO (e.g. 100, 200, 400, 800, 1600, Auto)")
    p_shutter.add_argument("--shutter", type=str, help="Set shutter speed (e.g. 1/125, 1/250, 1/500, 1s)")
    p_shutter.add_argument("--aperture", type=str, help="Set aperture (e.g. 2.8, 3.5, 5.6, 8.0, 11)")
    p_shutter.add_argument("--ec", type=str, help="Set exposure compensation (e.g. -1.0, 0, +1.0)")
    preset_choices = list(PRESETS.keys()) + [k.lower() for k in PRESETS.keys()]
    p_shutter.add_argument("--preset", type=str, choices=preset_choices, help="Apply shooting preset")
    p_shutter.add_argument("--mock", action="store_true", help="Run in mock mode")

    # timelapse
    p_tl = subparsers.add_parser("timelapse", help="Start automated timelapse intervalometer")
    p_tl.add_argument("-i", "--interval", type=float, required=True, help="Seconds between shots")
    p_tl.add_argument("-n", "--count", type=int, default=0, help="Total frames (0 = infinite)")
    p_tl.add_argument("--mock", action="store_true", help="Run in mock mode")

    # settings
    p_set = subparsers.add_parser("settings", help="View available quick settings and presets")
    p_set.add_argument("--mock", action="store_true", help="Run in mock mode")

    # info
    p_info = subparsers.add_parser("info", help="Camera and system diagnostics")
    p_info.add_argument("--mock", action="store_true", help="Run in mock mode")

    args = parser.parse_args()

    if not args.command:
        # Default to launching web server
        args.host = "0.0.0.0"
        args.port = 8000
        args.mock = False
        args.reload = False
        cmd_serve(args)
        return

    commands = {
        "serve": cmd_serve,
        "shutter": cmd_shutter,
        "timelapse": cmd_timelapse,
        "settings": cmd_settings,
        "info": cmd_info,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
