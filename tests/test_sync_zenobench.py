"""Sync copies only the pinned ZenoBench files Graph Manager uses; pull updates a clone."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from graph_manager.adapters import zenobench_sync


def commit_all(root: Path, message: str = "x") -> None:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-qm",
            message,
        ],
        check=True,
    )


def head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


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
    commit_all(root)


class SyncZenoBenchTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "ZenoBench"
        self.vendor = self.root / "vendor"
        self.fixtures = self.root / "fixtures"
        make_checkout(self.source)

    def sync(self, fixtures=True):
        return zenobench_sync.sync(self.source, self.vendor, self.fixtures if fixtures else None)

    def test_copies_skills_tasks_plans_and_commit(self):
        commit = self.sync()

        self.assertEqual(head(self.source), commit)
        self.assertEqual(commit + "\n", (self.vendor / "COMMIT").read_text())
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

    def test_without_fixtures_copies_no_plans(self):
        self.sync(fixtures=False)

        self.assertTrue((self.vendor / "COMMIT").is_file())
        self.assertFalse(self.fixtures.exists())


class PullZenoBenchTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.upstream = self.root / "upstream"
        self.checkout = self.root / "cache" / "ZenoBench"
        make_checkout(self.upstream)

    def pull(self):
        return zenobench_sync.pull(self.checkout, str(self.upstream))

    def test_clones_then_follows_new_upstream_commits(self):
        self.assertEqual(head(self.upstream), self.pull())

        (self.upstream / "skill_library" / "skills" / "skill_001" / "skill.json").write_text("[]")
        commit_all(self.upstream, "update")

        self.assertEqual(head(self.upstream), self.pull())
        self.assertEqual(head(self.upstream), head(self.checkout))

    def test_pulls_a_named_ref(self):
        first = head(self.upstream)
        subprocess.run(["git", "-C", str(self.upstream), "tag", "pinned"], check=True)
        (self.upstream / "skill_library" / "skills" / "skill_001" / "skill.json").write_text("[]")
        commit_all(self.upstream, "update")

        self.assertEqual(first, zenobench_sync.pull(self.checkout, str(self.upstream), "pinned"))

    def test_keeps_local_changes_that_a_pull_would_overwrite(self):
        self.pull()
        skill_json = self.checkout / "skill_library" / "skills" / "skill_001" / "skill.json"
        skill_json.write_text("local")
        (self.upstream / "skill_library" / "skills" / "skill_001" / "skill.json").write_text("[]")
        commit_all(self.upstream, "update")

        with self.assertRaises(subprocess.CalledProcessError):
            self.pull()
        self.assertEqual("local", skill_json.read_text())


if __name__ == "__main__":
    unittest.main()
