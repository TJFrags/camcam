import unittest
import time
import tempfile
import shutil
from pathlib import Path

from camcam.engine.mock_backend import MockCameraBackend
from camcam.engine.camera_manager import CameraManager
from camcam.engine.timelapse import TimelapseEngine


class TestTimelapse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.temp_path = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_timelapse_engine_execution(self):
        backend = MockCameraBackend(simulate_latency=False)
        backend.connect()
        cm = CameraManager(force_mock=True)
        cm.set_backend(backend)
        cm._storage_dir = self.temp_path

        engine = TimelapseEngine(cm)
        shots_recorded = []

        engine.add_on_shot_callback(lambda res: shots_recorded.append(res))

        # Start 3-shot timelapse with 0.5s interval
        self.assertTrue(engine.start(interval_seconds=0.5, total_shots=3))
        self.assertTrue(engine.get_status().active)

        # Wait for completion
        timeout = time.time() + 6.0
        while engine.get_status().active and time.time() < timeout:
            time.sleep(0.2)

        self.assertFalse(engine.get_status().active)
        self.assertEqual(len(shots_recorded), 3)
        self.assertEqual(engine.get_status().shots_taken, 3)


if __name__ == "__main__":
    unittest.main()
