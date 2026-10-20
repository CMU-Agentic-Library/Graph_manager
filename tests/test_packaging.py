"""The default public Skill Library is available from an installed wheel."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_wheel_contains_synced_zenobench_library(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["uv", "build", "--wheel", "--out-dir", directory],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            wheels = list(Path(directory).glob("*.whl"))
            self.assertEqual(1, len(wheels))
            with ZipFile(wheels[0]) as wheel:
                names = wheel.namelist()
                vendor = "graph_manager/vendor/zenobench/"
                self.assertIn(vendor + "COMMIT", names)
                self.assertIn(vendor + "tasks.json", names)
                self.assertIn(vendor + "skills/skill_017/SKILL.md", names)
                self.assertIn(vendor + "skills/skill_017/skill.json", names)
                self.assertFalse(any(name.startswith("skill_library/") for name in names))


if __name__ == "__main__":
    unittest.main()
