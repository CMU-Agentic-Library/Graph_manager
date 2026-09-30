import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from skill_library.viewer.server import make_server


class SkillLibraryViewerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.library = root / "skill_library.yaml"
        self.page = root / "index.html"
        self.page.write_text("<html><body>Skill Library</body></html>")
        self.library.write_text("version: 1\nskills:\n  - id: skill_001\n    name: First name\nconnections: []\n")
        self.server = make_server(self.library, self.page, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def test_api_reads_current_yaml_on_each_request(self):
        with urlopen(self.base + "/api/library") as response:
            first = json.load(response)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(first["skills"][0]["name"], "First name")

        self.library.write_text("version: 1\nskills:\n  - id: skill_001\n    name: Updated name\nconnections: []\n")
        with urlopen(self.base + "/api/library") as response:
            second = json.load(response)
        self.assertEqual(second["skills"][0]["name"], "Updated name")

    def test_page_and_yaml_error_are_served_without_leaking_a_traceback(self):
        with urlopen(self.base + "/") as response:
            self.assertIn("Skill Library", response.read().decode())

        self.library.write_text("skills: [unterminated\n")
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/library")
        self.assertEqual(error.exception.code, 422)
        body = json.load(error.exception)
        self.assertIn("error", body)
        self.assertNotIn("Traceback", json.dumps(body))


if __name__ == "__main__":
    unittest.main()
