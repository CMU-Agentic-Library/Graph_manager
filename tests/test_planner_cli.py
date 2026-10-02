import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class SequenceHandler(BaseHTTPRequestHandler):
    outputs = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        self.rfile.read(length)
        text = self.outputs.pop(0)
        data = json.dumps({"choices": [{"message": {"content": text}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


class PlannerCliTest(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), SequenceHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_cli_writes_validated_result_with_optional_catalog(self):
        SequenceHandler.outputs = [
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "subgoal_plan",
                    "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
                }
            ),
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "skill_subgraph",
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
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "entities.json"
            output = root / "result.json"
            catalog.write_text(
                json.dumps({"entities": [{"id": "apple", "types": ["MovableObject"]}]})
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "graph_manager.cli",
                    "--goal",
                    "Hold the apple",
                    "--entity-catalog",
                    str(catalog),
                    "--base-url",
                    f"http://127.0.0.1:{self.server.server_port}/v1",
                    "--model",
                    "local-vlm",
                    "--output",
                    str(output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            saved = json.loads(output.read_text())
            self.assertEqual("statically_validated", saved["status"])
            self.assertEqual("skill_004", saved["subgraphs"][0]["nodes"][0]["skill_id"])


if __name__ == "__main__":
    unittest.main()
