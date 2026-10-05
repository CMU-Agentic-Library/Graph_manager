"""The default public Skill Library is available from an installed wheel."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_wheel_contains_default_skill_library(self):
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
                self.assertIn("skill_library/skill_library.json", wheel.namelist())


if __name__ == "__main__":
    unittest.main()
