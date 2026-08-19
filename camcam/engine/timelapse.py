"""
Timelapse and Intervalometer Engine for CamCam (Shutter Trigger Only)
"""

import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable, List
from camcam.engine.base import CaptureResult
from camcam.engine.camera_manager import CameraManager


@dataclass
class TimelapseStatus:
    active: bool = False
    interval_seconds: float = 5.0
    total_shots: int = 0  # 0 = continuous
    shots_taken: int = 0
    start_time: Optional[float] = None
    last_shot_time: Optional[float] = None
    next_shot_time: Optional[float] = None
    error_count: int = 0


class TimelapseEngine:
    """Manages background automated timelapse intervalometer."""

    def __init__(self, camera_manager: CameraManager):
        self.camera_manager = camera_manager
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[CaptureResult], None]] = []
        self._status = TimelapseStatus()
        self._lock = threading.Lock()

    def add_on_shot_callback(self, callback: Callable[[CaptureResult], None]):
        self._callbacks.append(callback)

    def get_status(self) -> TimelapseStatus:
        with self._lock:
            return TimelapseStatus(
                active=self._status.active,
                interval_seconds=self._status.interval_seconds,
                total_shots=self._status.total_shots,
                shots_taken=self._status.shots_taken,
                start_time=self._status.start_time,
                last_shot_time=self._status.last_shot_time,
                next_shot_time=self._status.next_shot_time,
                error_count=self._status.error_count,
            )

    def start(self, interval_seconds: float, total_shots: int = 0) -> bool:
        with self._lock:
            if self._status.active:
                return False

            self._stop_event.clear()
            self._status.active = True
            self._status.interval_seconds = max(0.5, float(interval_seconds))
            self._status.total_shots = total_shots
            self._status.shots_taken = 0
            self._status.start_time = time.time()
            self._status.error_count = 0

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._status.active:
                return False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        with self._lock:
            self._status.active = False
        return True

    def _run_loop(self):
        while not self._stop_event.is_set():
            with self._lock:
                current_shot = self._status.shots_taken + 1
                total = self._status.total_shots

            # Check if reached target
            if total > 0 and current_shot > total:
                break

            try:
                res = self.camera_manager.capture_image(delay=0.0)
                with self._lock:
                    if res.success:
                        self._status.shots_taken += 1
                        self._status.last_shot_time = time.time()
                    else:
                        self._status.error_count += 1

                for cb in self._callbacks:
                    try:
                        cb(res)
                    except Exception:
                        pass

            except Exception:
                with self._lock:
                    self._status.error_count += 1

            with self._lock:
                if total > 0 and self._status.shots_taken >= total:
                    break
                interval = self._status.interval_seconds
                self._status.next_shot_time = time.time() + interval

            sleep_end = time.time() + interval
            while time.time() < sleep_end and not self._stop_event.is_set():
                time.sleep(0.1)

        with self._lock:
            self._status.active = False
