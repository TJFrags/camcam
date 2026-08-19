#!/usr/bin/env python3
"""
Nikon D3100 Timelapse & Intervalometer Script
"""

import argparse
import sys
import time
from pathlib import Path
from camcam.engine import CameraEngine


def main():
    parser = argparse.ArgumentParser(description="Nikon D3100 Intervalometer / Timelapse")
    parser.add_argument("-i", "--interval", type=float, required=True, help="Interval between shots in seconds (e.g. 5, 10, 30)")
    parser.add_argument("-n", "--count", type=int, default=0, help="Total number of frames (0 = continuous until Ctrl+C)")
    parser.add_argument("-d", "--delay", type=float, default=0.0, help="Initial startup delay in seconds")
    parser.add_argument("-o", "--output", type=str, default="./photos/timelapse", help="Output directory")
    parser.add_argument("--mock", action="store_true", help="Run in simulator mode")

    args = parser.parse_args()

    engine = CameraEngine(backend_type="mock" if args.mock else "auto", output_dir=args.output)

    print("=" * 60)
    print("      TIMELAPSE INTERVALOMETER ACTIVE")
    print(f"      Interval: {args.interval}s | Target: {'Continuous' if args.count == 0 else f'{args.count} frames'}")
    print(f"      Output: {Path(args.output).resolve()}")
    print("      Press Ctrl+C at any time to stop.")
    print("=" * 60)

    if args.delay > 0:
        print(f"Starting in {args.delay} seconds...")
        time.sleep(args.delay)

    frame = 0
    try:
        while True:
            frame += 1
            if args.count > 0 and frame > args.count:
                break

            print(f"\n[Frame {frame}{f'/{args.count}' if args.count > 0 else ''}] Capturing...")
            saved = engine.snap(filename_prefix=f"TL_{frame:05d}")
            
            if args.count > 0 and frame == args.count:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n[!] Timelapse stopped by user.")
    finally:
        engine.close()
        print(f"\nFinished. Total frames recorded: {frame - 1 if (args.count > 0 and frame > args.count) else frame}")


if __name__ == "__main__":
    main()
