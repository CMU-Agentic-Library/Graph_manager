"""Episode logs keep everything, including task_status, and the camera images."""

import json
import tempfile
import unittest
from pathlib import Path

from graph_manager.application.orchestration.trajectory import (
    DirectoryRecorder,
    MemoryRecorder,
    observation_record,
)
from graph_manager.domain.env_types import CameraImage, Observation

OBSERVATION = Observation(
    (CameraImage("head", b"head-png"),),
    {
        "objects": [{"name": "apple", "kind": "object", "position": [1.0, 2.0, 0.5]}],
        "robot": {"base_pose": [0, 0, 0]},
        "task_status": [{"atom": "inside(apple, fruit_basket)", "holds": False}],
    },
)


class TrajectoryTest(unittest.TestCase):
    def test_observation_record_keeps_task_status_but_not_image_bytes(self):
        record = observation_record(OBSERVATION)
        self.assertEqual(
            [{"atom": "inside(apple, fruit_basket)", "holds": False}], record["task_status"]
        )
        self.assertEqual(["head"], record["cameras"])
        self.assertEqual("apple", record["objects"][0]["name"])
        json.dumps(record)

    def test_directory_recorder_appends_events_and_saves_images(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = DirectoryRecorder(Path(directory) / "attempt_1")
            recorder.event("started", {"exp_id": "e1"})
            recorder.event("check", {"success": True})
            recorder.images("00_start", OBSERVATION)

            lines = (Path(directory) / "attempt_1" / "trajectory.jsonl").read_text().splitlines()
            self.assertEqual(["started", "check"], [json.loads(line)["kind"] for line in lines])
            self.assertEqual("e1", json.loads(lines[0])["exp_id"])
            image = Path(directory) / "attempt_1" / "images" / "00_start_head.png"
            self.assertEqual(b"head-png", image.read_bytes())

    def test_memory_recorder(self):
        recorder = MemoryRecorder()
        recorder.event("started", {"exp_id": "e1"})
        recorder.images("00_start", OBSERVATION)
        self.assertEqual(["started"], recorder.kinds())
        self.assertEqual(["00_start"], recorder.image_steps)


if __name__ == "__main__":
    unittest.main()
