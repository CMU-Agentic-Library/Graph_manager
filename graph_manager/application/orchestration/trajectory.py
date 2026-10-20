"""Per-episode records: an append-only event log and the camera images of each step."""

import dataclasses
import json
import time
from pathlib import Path
from typing import Protocol

from ...domain.env_types import Observation


def observation_record(observation: Observation) -> dict:
    """Everything except image bytes, including the evaluator's task_status (logs only)."""
    return {
        "objects": [dataclasses.asdict(o) for o in observation.objects],
        "robot": observation.robot,
        "task_status": list(observation.task_status),
        "cameras": [image.camera for image in observation.images],
    }


class EpisodeRecorder(Protocol):
    def event(self, kind: str, data: dict) -> None:
        raise NotImplementedError

    def images(self, step: str, observation: Observation) -> None:
        raise NotImplementedError


class MemoryRecorder:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []
        self.image_steps: list[str] = []

    def event(self, kind: str, data: dict) -> None:
        self.events.append((kind, data))

    def images(self, step: str, observation: Observation) -> None:
        self.image_steps.append(step)

    def kinds(self) -> list[str]:
        return [kind for kind, _ in self.events]


class DirectoryRecorder:
    """Writes <directory>/trajectory.jsonl and <directory>/images/<step>_<camera>.png."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        (self.directory / "images").mkdir(parents=True, exist_ok=True)
        self._log = self.directory / "trajectory.jsonl"

    def event(self, kind: str, data: dict) -> None:
        line = json.dumps({"time": time.time(), "kind": kind, **data}, ensure_ascii=False)
        with self._log.open("a", encoding="utf-8") as log:
            log.write(line + "\n")

    def images(self, step: str, observation: Observation) -> None:
        for image in observation.images:
            (self.directory / "images" / f"{step}_{image.camera}.png").write_bytes(image.png)
