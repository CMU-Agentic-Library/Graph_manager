"""Run many tasks with bounded concurrency, restarts, BUSY waits, and resumable results.

Each request gets <out>/<task_id>/<profile>/<variant>/seed_<seed>/result.json; the summary
reads those files separately (graph_manager.summary).
"""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from ...domain.env_types import TaskRequest
from ...ports import EnvironmentPortError
from .episode_runner import EpisodeResult

RunEpisode = Callable[[TaskRequest, Path], EpisodeResult]  # (request, attempt directory)
DECIDED = ("success", "failure")


@dataclass(frozen=True)
class BatchConfig:
    concurrency: int = 2
    max_restarts: int = 2  # new exps after a released one; 2 means at most 3 attempts
    busy_retry_s: float = 30
    busy_wait_max_s: float = 900


class BatchRunner:
    def __init__(
        self,
        run_episode: RunEpisode,
        out_dir: Path,
        config: BatchConfig = BatchConfig(),
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.run_episode = run_episode
        self.out_dir = Path(out_dir)
        self.config = config
        self.sleep = sleep
        self.clock = clock

    def run(self, requests: list[TaskRequest]) -> list[dict]:
        """Run every request; a request with a decided result.json from before is skipped."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as pool:
            return list(pool.map(self.run_task, requests))

    def run_task(self, request: TaskRequest) -> dict:
        task_dir = self.out_dir / request.path
        result_path = task_dir / "result.json"
        if result_path.exists():
            previous = json.loads(result_path.read_text())
            if previous.get("status") in DECIDED:
                return previous
        record = self._attempts(request, task_dir)
        task_dir.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        return record

    def _attempts(self, request: TaskRequest, task_dir: Path) -> dict:
        base = {"request": request.to_json()}
        failures: list[dict] = []
        busy_since: float | None = None
        while True:
            attempt_dir = task_dir / f"attempt_{len(failures) + 1}"
            try:
                episode = self.run_episode(request, attempt_dir)
            except EnvironmentPortError as exc:
                if exc.error_code == "BUSY":
                    now = self.clock()
                    busy_since = now if busy_since is None else busy_since
                    if now - busy_since < self.config.busy_wait_max_s:
                        self.sleep(self.config.busy_retry_s)
                        continue
                failures.append({"error_code": exc.error_code, "error": str(exc)})
                busy_since = None
                if (
                    exc.error_code == "BUSY"
                    or exc.bad_request  # an unknown task, variant, or profile stays unknown
                    or len(failures) > self.config.max_restarts
                ):
                    return {**base, "status": "error", "attempts": failures}
                continue
            except Exception as exc:  # a planner bug must not stop the other tasks
                failures.append(
                    {"error_code": "PLANNER_ERROR", "error": f"{type(exc).__name__}: {exc}"}
                )
                return {**base, "status": "error", "attempts": failures}
            if episode.reason == "model_error":  # no verdict from the model; resume reruns it
                return {
                    **base,
                    "status": "error",
                    "attempts": failures
                    + [
                        {
                            "error_code": "MODEL_ERROR",
                            "error": "the model call failed without output",
                        }
                    ],
                    "episode": episode.to_json(),
                }
            return {
                **base,
                "status": episode.status,
                "attempts": failures,
                "episode": episode.to_json(),
            }
