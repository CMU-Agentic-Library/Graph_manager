"""The separate Harness command wires the SDK session into planning."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_manager.harness_cli import run


class FakeHarnessSession:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_id = kwargs["session_id"] or "generated-session"
        self.dsh_home = Path(kwargs["dsh_home"])
        self.prompts = []
        self.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def ask(self, text, image=None, image_mime="image/jpeg"):
        self.prompts.append((text, image, image_mime))
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


class HarnessCliTest(unittest.TestCase):
    def test_separate_command_saves_session_id_and_plan(self):
        FakeHarnessSession.created = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "scene.png"
            image.write_bytes(b"image-bytes")
            patch_file = root / "route.patch.yml"
            patch_file.write_text("[]\n")
            output = root / "plan.json"
            with patch("graph_manager.harness_cli.DeepSeekHarnessSession", FakeHarnessSession):
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
                        "--patch",
                        str(patch_file),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(0, exit_code)
            saved = json.loads(output.read_text())
            self.assertEqual("generated-session", saved["runtime"]["session_id"])
            self.assertEqual("deepseek_harness", saved["runtime"]["backend"])
            self.assertEqual("unresolved_references", saved["status"])
            session = FakeHarnessSession.created[0]
            self.assertEqual("sdk", session.kwargs["profile"])
            self.assertEqual(b"image-bytes", session.prompts[0][1])
            self.assertEqual("image/png", session.prompts[0][2])


if __name__ == "__main__":
    unittest.main()
