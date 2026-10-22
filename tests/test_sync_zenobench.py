"""The sync script copies only the pinned ZenoBench files Graph Manager uses."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_zenobench", ROOT / "scripts" / "sync_zenobench.py"
)
sync_zenobench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_zenobench)


def make_checkout(root: Path) -> None:
    library = root / "skill_library"
    skill = library / "skills" / "skill_001"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: navigate-place\ndescription: Go.\n---\n")
    (skill / "skill.json").write_text("{}")
    (library / "plans").mkdir()
    (library / "plans" / "collect_fruits.skill_subgraph.json").write_text("{}")
    (library / "plans" / "summary.json").write_text("[]")
    (library / "tasks.json").write_text(
        '{"tasks": [{"task_id": "collect_fruits", "goal": {}, "variants": {"default": {}}}]}'
    )
    benchmark = root / "benchmark" / "v3"
    benchmark.mkdir(parents=True)
    (benchmark / "tasks.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T01",
                        "goal": {"all": ["secret"]},
                        "routes": {},
                        "variants": {
                            "plain": {"note": "secret"},
                            "blocked": {"conditions": ["no_overhang"]},
                            "far": {"conditions": ["start_elsewhere", "no_overhang"]},
                            "probe": {"difficulty": "diagnostic"},
                        },
                    }
                ]
            }
        )
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        check=True,
    )


class SyncZenoBenchTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "ZenoBench"
        self.vendor = self.root / "vendor"
        self.fixtures = self.root / "fixtures"
        make_checkout(self.source)

    def sync(self):
        return sync_zenobench.sync(self.source, self.vendor, self.fixtures)

    def test_copies_skills_tasks_plans_and_commit(self):
        commit = self.sync()

        head = subprocess.run(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(head, commit)
        self.assertEqual(head + "\n", (self.vendor / "COMMIT").read_text())
        self.assertTrue((self.vendor / "skills" / "skill_001" / "SKILL.md").is_file())
        self.assertTrue((self.vendor / "skills" / "skill_001" / "skill.json").is_file())
        index = json.loads((self.vendor / "tasks.json").read_text())
        self.assertEqual(
            [
                {
                    "task_id": "collect_fruits",
                    "catalog": "skill_library/tasks.json",
                    "default_profile": "gt",
                    "variants": {"default": "easy"},
                },
                {
                    "task_id": "T01",
                    "catalog": "benchmark/v3/tasks.json",
                    "default_profile": "benchmark",
                    "variants": {
                        "plain": "easy",
                        "blocked": "medium",
                        "far": "hard",
                        "probe": "diagnostic",
                    },
                },
            ],
            index["tasks"],
        )
        self.assertNotIn("secret", (self.vendor / "tasks.json").read_text())
        self.assertEqual(
            ["collect_fruits.skill_subgraph.json"],
            sorted(p.name for p in self.fixtures.iterdir()),
        )

    def test_resync_removes_skills_deleted_upstream(self):
        stale = self.vendor / "skills" / "skill_999"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("old")

        self.sync()

        self.assertFalse(stale.exists())

    def test_refuses_uncommitted_library_changes(self):
        (self.source / "skill_library" / "tasks.json").write_text('{"tasks": [1]}')

        with self.assertRaisesRegex(ValueError, "uncommitted"):
            self.sync()
        self.assertFalse(self.vendor.exists())


if __name__ == "__main__":
    unittest.main()
