"""Batch runs restart released exps, wait out BUSY, and resume from earlier results."""

import json
import tempfile
import threading
import unittest
from pathlib import Path

from graph_manager.application.orchestration.batch_runner import BatchConfig, BatchRunner
from graph_manager.application.orchestration.episode_runner import EpisodeResult
from graph_manager.domain.env_types import TaskRequest
from graph_manager.ports import EnvironmentPortError
from graph_manager.summary import summarize_dir

BUSY = EnvironmentPortError("busy", error_code="BUSY", http_status=503)
GONE = EnvironmentPortError("crashed", error_code="SIM_CRASHED", http_status=500)
NO_VARIANT = EnvironmentPortError("no", error_code="UNKNOWN_VARIANT", http_status=400)


def request(task_id):
    return TaskRequest(task_id, profile="gt")


def episode(task_id, status="success", reason="model_finished"):
    return EpisodeResult(
        request(task_id).to_json(),
        {"name": "gt", "observation": ["images"], "max_calls": 40},
        f"{task_id}-exp",
        "s",
        status,
        reason,
        (),
        (),
        {"variant": "default", "difficulty": "easy"},
        0,
        1,
        1,
        2,
        0,
        1.0,
    )


class Script:
    """Stands in for run_episode: each task returns or raises its scripted outcomes in turn."""

    def __init__(self, **outcomes):
        self.outcomes = {task: list(items) for task, items in outcomes.items()}
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, task_request, attempt_dir):
        task_id = task_request.task_id
        with self.lock:
            self.calls.append((task_id, attempt_dir.name))
            outcome = self.outcomes[task_id].pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class BatchRunnerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.out = Path(directory.name)
        self.sleeps = []

    def runner(self, script, **config):
        return BatchRunner(script, self.out, BatchConfig(**config), sleep=self.sleeps.append)

    def task_dir(self, task_id):
        return self.out / request(task_id).path

    def result(self, task_id):
        return json.loads((self.task_dir(task_id) / "result.json").read_text())

    def run_tasks(self, runner, *task_ids):
        runner.run([request(task_id) for task_id in task_ids])
        return summarize_dir(self.out, ("difficulty",))

    def test_statuses_files_and_summary(self):
        script = Script(a=[episode("a")], b=[episode("b", "failure")])
        summary = self.run_tasks(self.runner(script), "a", "b")

        overall = summary["overall"]
        self.assertEqual(
            (2, 1, 1, 0, 0.5),
            tuple(overall[k] for k in ("runs", "success", "failure", "error", "success_rate")),
        )
        self.assertEqual({"model_finished": 2}, overall["reasons"])
        self.assertEqual(2.0, overall["mean_model_turns"])
        self.assertEqual(2, summary["by"]["difficulty"]["easy"]["runs"])
        self.assertEqual("success", self.result("a")["status"])
        self.assertEqual("a-exp", self.result("a")["episode"]["exp_id"])
        self.assertEqual({"task_id": "a", "seed": 0, "profile": "gt"}, self.result("a")["request"])

    def test_bad_request_is_not_retried(self):
        script = Script(a=[NO_VARIANT])

        summary = self.run_tasks(self.runner(script), "a")

        self.assertEqual(1, len(script.calls))
        self.assertEqual({"UNKNOWN_VARIANT": 1}, summary["overall"]["error_codes"])
        self.assertEqual(1, summary["by"]["difficulty"]["None"]["error"])

    def test_busy_is_retried_in_the_same_attempt(self):
        script = Script(a=[BUSY, BUSY, episode("a")])

        self.run_tasks(self.runner(script), "a")

        self.assertEqual([30, 30], self.sleeps)
        self.assertEqual([("a", "attempt_1")] * 3, script.calls)
        self.assertEqual([], self.result("a")["attempts"])

    def test_busy_for_too_long_is_an_error(self):
        self.run_tasks(self.runner(Script(a=[BUSY]), busy_wait_max_s=0), "a")

        self.assertEqual("error", self.result("a")["status"])
        self.assertEqual("BUSY", self.result("a")["attempts"][0]["error_code"])

    def test_released_exp_restarts_up_to_the_limit(self):
        script = Script(a=[GONE, GONE, episode("a")], b=[GONE, GONE, GONE])

        summary = self.run_tasks(self.runner(script, concurrency=1), "a", "b")

        self.assertEqual("success", self.result("a")["status"])
        self.assertEqual(2, len(self.result("a")["attempts"]))
        self.assertEqual("error", self.result("b")["status"])
        self.assertEqual(3, len(self.result("b")["attempts"]))
        self.assertEqual(
            ["attempt_1", "attempt_2", "attempt_3"],
            [name for task, name in script.calls if task == "b"],
        )
        self.assertEqual(1.0, summary["overall"]["success_rate"])
        self.assertEqual(2, summary["overall"]["restarts"])

    def test_planner_bug_is_an_error_and_other_tasks_still_run(self):
        script = Script(a=[KeyError("subgoal")], b=[episode("b")])

        summary = self.run_tasks(self.runner(script), "a", "b")["overall"]

        self.assertEqual("PLANNER_ERROR", self.result("a")["attempts"][0]["error_code"])
        self.assertEqual((1, 1), (summary["error"], summary["success"]))

    def test_model_error_is_an_error_and_not_restarted(self):
        script = Script(a=[episode("a", "failure", "model_error")], b=[episode("b")])

        summary = self.run_tasks(self.runner(script), "a", "b")["overall"]

        result = self.result("a")
        self.assertEqual("error", result["status"])
        self.assertEqual("MODEL_ERROR", result["attempts"][-1]["error_code"])
        self.assertEqual("model_error", result["episode"]["reason"])
        self.assertEqual(1, sum(1 for task, _ in script.calls if task == "a"))
        self.assertEqual(
            (1, 1, 1.0), (summary["error"], summary["success"], summary["success_rate"])
        )

    def test_resume_keeps_decided_results_and_reruns_errors(self):
        for task_id, status in (("a", "success"), ("b", "error")):
            self.task_dir(task_id).mkdir(parents=True)
            (self.task_dir(task_id) / "result.json").write_text(
                json.dumps({"request": {"task_id": task_id}, "status": status, "attempts": []})
            )
        script = Script(b=[episode("b")])

        summary = self.run_tasks(self.runner(script), "a", "b")["overall"]

        self.assertEqual([("b", "attempt_1")], script.calls)
        self.assertEqual(2, summary["success"])


if __name__ == "__main__":
    unittest.main()
