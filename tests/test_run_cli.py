"""graph-manager-run wires the environment, Harness sessions, and the batch runner."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.env_types import (
    CameraImage,
    ContractResult,
    ExecutionReply,
    GoalCheck,
    Observation,
    Profile,
    StartedTask,
    TaskInfo,
)
from graph_manager.run_cli import run

OBS = Observation((CameraImage("head", b"h"),), {"robot": {}})
PLAN = {
    "schema_version": 2,
    "kind": "task_plan",
    "subgoals": [{"id": "a", "goal": "Hold apple"}],
    "subgraphs": [
        {
            "schema_version": 2,
            "kind": "skill_subgraph",
            "subgoal_id": "a",
            "nodes": [
                {
                    "id": "n1",
                    "skill": "pick",
                    "args": {"object": {"ref": "apple"}},
                    "depends_on": [],
                }
            ],
        }
    ],
}


class FakeEnvironment:
    requests = []

    def __init__(self, base_url):
        self.base_url = base_url

    def initial_task(self, request):
        self.requests.append(request)
        task = TaskInfo(request.task_id, request.task_id, "Collect fruits.")
        return StartedTask("exp-1", task, Profile(request.profile, ("images", "robot"), 40), OBS)

    def do_contract(self, exp_id, calls):
        results = tuple(
            ContractResult(c.contract, c.args, True, None, None, (), (), {}, None) for c in calls
        )
        return ExecutionReply(exp_id, results, OBS)

    def check_task(self, exp_id):
        return GoalCheck(exp_id, True, (), (), {"variant": "default"})


class FakeHarnessSession:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_id = kwargs["session_id"]
        self.replies = [json.dumps(PLAN), json.dumps({"kind": "finish"})]
        self.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def ask(self, text, images=()):
        return self.replies.pop(0)


class RunCliTest(unittest.TestCase):
    def setUp(self):
        FakeHarnessSession.created = []
        FakeEnvironment.requests = []
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def invoke(self, *extra):
        argv = [
            "--out",
            str(self.root / "runs"),
            "--dsh-home",
            str(self.root / "dsh"),
            "--model",
            "local-vlm",
            *extra,
        ]
        with (
            patch("graph_manager.run_cli.HttpEnvironment", FakeEnvironment),
            patch("graph_manager.harness_args.DeepSeekHarnessSession", FakeHarnessSession),
        ):
            return run(argv)

    def test_runs_a_task_and_writes_results(self):
        exit_code = self.invoke("--task", "collect_fruits", "--env-url", "http://env:8800")

        self.assertEqual(0, exit_code)
        runs = self.root / "runs"
        task_dir = runs / "collect_fruits" / "gt" / "any" / "seed_0"
        result = json.loads((task_dir / "result.json").read_text())
        self.assertEqual("success", result["status"])
        self.assertEqual("model_finished", result["episode"]["reason"])
        self.assertTrue((task_dir / "attempt_1" / "trajectory.jsonl").is_file())
        self.assertTrue((task_dir / "attempt_1" / "images" / "00_start_head.png").is_file())
        info = json.loads((runs / "run.json").read_text())
        self.assertEqual(ZenoBenchLibrary().commit, info["zenobench_commit"])
        summary = json.loads((runs / "summary.json").read_text())
        self.assertEqual(1.0, summary["overall"]["success_rate"])
        self.assertEqual(1, summary["by"]["profile"]["gt"]["success"])
        session = FakeHarnessSession.created[0]
        self.assertTrue(session.session_id.startswith("collect_fruits-"))
        self.assertEqual(ZenoBenchLibrary().skills_dir, session.kwargs["skills_dir"])

    def test_requests_cover_tasks_and_seeds_and_skip_missing_difficulties(self):
        exit_code = self.invoke(
            "--all",
            "--catalog",
            "benchmark/v3/tasks.json",
            "--difficulty",
            "hard",
            "--seed",
            "10-11",
            "--env-profile",
            "gt",
            "--env-url",
            "http://env",
        )

        self.assertEqual(0, exit_code)
        requests = FakeEnvironment.requests
        self.assertEqual(24, len(requests))  # 12 tasks with a hard variant, 2 seeds each
        self.assertEqual({"gt"}, {r.profile for r in requests})
        self.assertEqual({10, 11}, {r.seed for r in requests})
        self.assertNotIn("T11_collect_fruits", {r.task_id for r in requests})
        self.assertTrue(
            (
                self.root
                / "runs"
                / "T06_block_destination_occupied"
                / "gt"
                / "difficulty-hard"
                / "seed_10"
                / "result.json"
            ).is_file()
        )

    def test_input_errors(self):
        self.assertEqual(2, self.invoke("--task", "no_such_task", "--env-url", "http://env"))
        self.assertEqual(
            2,
            self.invoke("--task", "collect_fruits", "--variant", "x", "--env-url", "http://env"),
        )
        self.assertEqual(
            2,
            self.invoke(
                "--task", "T14_shelve_the_book", "--difficulty", "easy", "--env-url", "http://env"
            ),
        )
        with patch.dict("os.environ", {"ZENOBENCH_ENV_URL": ""}):
            self.assertEqual(2, self.invoke("--task", "collect_fruits"))


if __name__ == "__main__":
    unittest.main()
