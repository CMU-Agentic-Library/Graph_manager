"""The public command wires Harness, the ZenoBench skills, and the planning service."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.cli import run
from graph_manager.domain.models import ImageInput

PLAN = {
    "schema_version": 2,
    "kind": "task_plan",
    "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
    "subgraphs": [
        {
            "schema_version": 2,
            "kind": "skill_subgraph",
            "subgoal_id": "sg_1",
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


class FakeHarnessSession:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_id = kwargs["session_id"] or "generated-session"
        self.dsh_home = Path(kwargs["dsh_home"])
        self.turns = []
        self.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def ask(self, text, images=()):
        self.turns.append((text, images))
        return json.dumps(PLAN)


class PlannerCliTest(unittest.TestCase):
    def setUp(self):
        FakeHarnessSession.created = []

    def test_public_command_saves_plan_skill_commit_and_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "scene.png"
            image.write_bytes(b"pixels")
            output = root / "plan.json"

            with patch("graph_manager.cli.DeepSeekHarnessSession", FakeHarnessSession):
                exit_code = run(
                    [
                        "--goal",
                        "Hold apple",
                        "--image",
                        str(image),
                        "--dsh-home",
                        str(root / "dsh"),
                        "--provider",
                        "lab-vlm",
                        "--model",
                        "local-vlm",
                        "--output",
                        str(output),
                    ]
                )

            saved = json.loads(output.read_text())
            library = ZenoBenchLibrary()
            self.assertEqual(0, exit_code)
            self.assertEqual("statically_validated", saved["status"])
            self.assertEqual(PLAN, saved["task_plan"])
            self.assertEqual(
                {"source": "ZenoBench", "commit": library.commit}, saved["skill_library"]
            )
            self.assertEqual("generated-session", saved["runtime"]["session_id"])
            session = FakeHarnessSession.created[0]
            self.assertEqual(library.skills_dir, session.kwargs["skills_dir"])
            self.assertEqual((ImageInput(b"pixels", "image/png"),), session.turns[0][1])


if __name__ == "__main__":
    unittest.main()
