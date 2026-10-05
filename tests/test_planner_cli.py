"""The public command wires Harness to the single planning service."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_manager.cli import run


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

    def ask(self, text, image=None, image_mime="image/jpeg"):
        self.turns.append((text, image, image_mime))
        return json.dumps(
            {
                "schema_version": 1,
                "kind": "task_plan",
                "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
                "subgraphs": [
                    {
                        "subgoal_id": "sg_1",
                        "nodes": [
                            {
                                "id": "n1",
                                "skill_id": "skill_004",
                                "args": {"object": {"ref": "apple"}},
                                "depends_on": [],
                            }
                        ],
                    }
                ],
            }
        )


class PlannerCliTest(unittest.TestCase):
    def setUp(self):
        FakeHarnessSession.created = []

    def test_public_command_saves_grounded_plan_and_session_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "scene.png"
            image.write_bytes(b"pixels")
            catalog = root / "entities.json"
            catalog.write_text(
                json.dumps({"entities": [{"id": "apple", "types": ["MovableObject"]}]})
            )
            patch_file = root / "route.patch.yml"
            patch_file.write_text("[]\n")
            output = root / "plan.json"

            with patch("graph_manager.cli.DeepSeekHarnessSession", FakeHarnessSession):
                exit_code = run(
                    [
                        "--goal",
                        "Hold apple",
                        "--image",
                        str(image),
                        "--entity-catalog",
                        str(catalog),
                        "--dsh-home",
                        str(root / "dsh"),
                        "--provider",
                        "lab-vlm",
                        "--model",
                        "local-vlm",
                        "--patch",
                        str(patch_file),
                        "--output",
                        str(output),
                    ]
                )

            saved = json.loads(output.read_text())
            self.assertEqual(0, exit_code)
            self.assertEqual("statically_validated", saved["status"])
            self.assertEqual("deepseek_harness", saved["runtime"]["backend"])
            self.assertEqual("generated-session", saved["runtime"]["session_id"])
            session = FakeHarnessSession.created[0]
            self.assertEqual("sdk", session.kwargs["profile"])
            self.assertEqual(b"pixels", session.turns[0][1])
            self.assertEqual("image/png", session.turns[0][2])


if __name__ == "__main__":
    unittest.main()
