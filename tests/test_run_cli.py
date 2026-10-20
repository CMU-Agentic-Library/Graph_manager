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
    StartedTask,
    TaskInfo,
)
from graph_manager.run_cli import run

OBS = Observation((CameraImage("head", b"h"),), (), {}, ())
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
    def __init__(self, base_url):
        self.base_url = base_url

    def initial_task(self, task_id):
        return StartedTask("exp-1", TaskInfo(task_id, task_id, "Collect fruits."), OBS)

    def do_contract(self, exp_id, calls):
        results = tuple(
            ContractResult(c.contract, c.args, True, None, None, (), (), {}, None) for c in calls
        )
        return ExecutionReply(exp_id, results, OBS)

    def check_task(self, exp_id):
        return GoalCheck(exp_id, True, ())


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
        result = json.loads((runs / "collect_fruits" / "result.json").read_text())
        self.assertEqual("success", result["status"])
        self.assertEqual("model_finished", result["episode"]["reason"])
        self.assertTrue((runs / "collect_fruits" / "attempt_1" / "trajectory.jsonl").is_file())
        self.assertTrue(
            (runs / "collect_fruits" / "attempt_1" / "images" / "00_start_head.png").is_file()
        )
        info = json.loads((runs / "run.json").read_text())
        self.assertEqual(ZenoBenchLibrary().commit, info["zenobench_commit"])
        self.assertEqual(1.0, json.loads((runs / "summary.json").read_text())["success_rate"])
        session = FakeHarnessSession.created[0]
        self.assertTrue(session.session_id.startswith("collect_fruits-"))
        self.assertEqual(ZenoBenchLibrary().skills_dir, session.kwargs["skills_dir"])

    def test_input_errors(self):
        self.assertEqual(2, self.invoke("--task", "no_such_task", "--env-url", "http://env"))
        with patch.dict("os.environ", {"ZENOBENCH_ENV_URL": ""}):
            self.assertEqual(2, self.invoke("--task", "collect_fruits"))


if __name__ == "__main__":
    unittest.main()
