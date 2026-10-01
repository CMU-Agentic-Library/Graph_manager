import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from skill_library.viewer.server import make_server


class SkillLibraryViewerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.library = root / "skill_library.json"
        self.page = root / "index.html"
        self.page.write_text("<html><body>Skill Library</body></html>")
        self.library.write_text(json.dumps({"version": 1, "skills": [{"id": "skill_001", "name": "First name"}], "connections": []}))
        self.server = make_server(self.library, self.page, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def test_api_reads_current_json_on_each_request(self):
        with urlopen(self.base + "/api/library") as response:
            first = json.load(response)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(first["skills"][0]["name"], "First name")

        self.library.write_text(json.dumps({"version": 1, "skills": [{"id": "skill_001", "name": "Updated name"}], "connections": []}))
        with urlopen(self.base + "/api/library") as response:
            second = json.load(response)
        self.assertEqual(second["skills"][0]["name"], "Updated name")

    def test_page_and_json_error_are_served_without_leaking_a_traceback(self):
        with urlopen(self.base + "/") as response:
            self.assertIn("Skill Library", response.read().decode())

        self.library.write_text('{"skills": [unterminated')
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/library")
        self.assertEqual(error.exception.code, 422)
        body = json.load(error.exception)
        self.assertIn("error", body)
        self.assertNotIn("Traceback", json.dumps(body))

    def test_rejects_json_without_skills_list(self):
        self.library.write_text(json.dumps({"version": 1, "skills": {}}))
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/library")
        self.assertEqual(error.exception.code, 422)

    def test_rebuilds_json_library_when_contract_changes(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        root = self.library.parent
        skills = root / "skills"
        skills.mkdir()
        source = skills / "skill_001.json"
        source.write_text(json.dumps({"id": "skill_001", "name": "From source"}))
        (root / "types.json").write_text(json.dumps({"types": {}}))
        builder = root / "build.py"
        builder.write_text(
            "import json, pathlib\n"
            "root = pathlib.Path(__file__).parent\n"
            "skill = json.loads((root / 'skills' / 'skill_001.json').read_text())\n"
            "(root / 'skill_library.json').write_text(json.dumps({'version': 1, 'skills': [skill]}))\n"
        )
        self.library.unlink()
        self.server = make_server(self.library, self.page, port=0, builder_path=builder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        with urlopen(self.base + "/api/library") as response:
            self.assertEqual(json.load(response)["skills"][0]["name"], "From source")
        time.sleep(0.02)
        source.write_text(json.dumps({"id": "skill_001", "name": "Changed source"}))
        with urlopen(self.base + "/api/library") as response:
            self.assertEqual(json.load(response)["skills"][0]["name"], "Changed source")

    def test_only_catalog_api_is_exposed(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/source-index")
        self.assertEqual(error.exception.code, 404)

    def test_rebuilds_after_source_contract_is_deleted(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        root = self.library.parent
        skills = root / "skills"
        skills.mkdir()
        for number in (1, 2):
            (skills / f"skill_{number:03}.json").write_text(json.dumps({"id": f"skill_{number:03}"}))
        (root / "types.json").write_text(json.dumps({"types": {}}))
        builder = root / "build.py"
        builder.write_text(
            "import json, pathlib\n"
            "root = pathlib.Path(__file__).parent\n"
            "skills = [json.loads(p.read_text()) for p in sorted((root / 'skills').glob('skill_*.json'))]\n"
            "(root / 'skill_library.json').write_text(json.dumps({'version': 1, 'skills': skills}))\n"
        )
        self.library.unlink()
        self.server = make_server(self.library, self.page, port=0, builder_path=builder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        with urlopen(self.base + "/api/library") as response:
            self.assertEqual(2, len(json.load(response)["skills"]))
        (skills / "skill_002.json").unlink()
        with urlopen(self.base + "/api/library") as response:
            self.assertEqual(["skill_001"], [skill["id"] for skill in json.load(response)["skills"]])

    def test_does_not_rebuild_repeatedly_when_id_differs_from_filename(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        root = self.library.parent
        skills = root / "skills"
        skills.mkdir()
        (skills / "skill_001.json").write_text(json.dumps({"id": "navigate_v1"}))
        (root / "types.json").write_text(json.dumps({"types": {}}))
        builder = root / "build.py"
        builder.write_text(
            "import json, pathlib\n"
            "root = pathlib.Path(__file__).parent\n"
            "count = root / 'build_count.txt'\n"
            "count.write_text(str(int(count.read_text()) + 1 if count.exists() else 1))\n"
            "skill = json.loads((root / 'skills' / 'skill_001.json').read_text())\n"
            "(root / 'skill_library.json').write_text(json.dumps({'skills': [skill]}))\n"
        )
        self.library.unlink()
        self.server = make_server(self.library, self.page, port=0, builder_path=builder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        for _ in range(2):
            with urlopen(self.base + "/api/library") as response:
                self.assertEqual("navigate_v1", json.load(response)["skills"][0]["id"])
        self.assertEqual("1", (root / "build_count.txt").read_text())

    def test_rebuilds_malformed_aggregate_from_valid_sources(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        root = self.library.parent
        skills = root / "skills"
        skills.mkdir()
        (skills / "skill_001.json").write_text(json.dumps({"id": "skill_001"}))
        (root / "types.json").write_text(json.dumps({"types": {}}))
        builder = root / "build.py"
        builder.write_text(
            "import json, pathlib\n"
            "root = pathlib.Path(__file__).parent\n"
            "skill = json.loads((root / 'skills' / 'skill_001.json').read_text())\n"
            "(root / 'skill_library.json').write_text(json.dumps({'skills': [skill]}))\n"
        )
        self.library.write_text('{"skills": [unterminated')
        self.server = make_server(self.library, self.page, port=0, builder_path=builder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        with urlopen(self.base + "/api/library") as response:
            self.assertEqual("skill_001", json.load(response)["skills"][0]["id"])


if __name__ == "__main__":
    unittest.main()
