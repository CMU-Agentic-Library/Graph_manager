import base64
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from graph_manager.openai_compatible import ModelAdapterError, OpenAICompatibleModel


class FakeChatHandler(BaseHTTPRequestHandler):
    requests = []
    response = {"choices": [{"message": {"content": '{"kind":"subgoal_plan"}'}}]}

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        self.requests.append(
            (self.path, self.headers.get("Authorization"), json.loads(self.rfile.read(length)))
        )
        data = json.dumps(self.response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


class OpenAICompatibleModelTest(unittest.TestCase):
    def setUp(self):
        FakeChatHandler.requests = []
        FakeChatHandler.response = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        self.server = HTTPServer(("127.0.0.1", 0), FakeChatHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_multimodal_json_request_and_response(self):
        model = OpenAICompatibleModel(
            f"http://127.0.0.1:{self.server.server_port}/v1", "local-vlm", api_key="test-key"
        )
        self.assertEqual(
            '{"ok":true}', model.generate("Task and Library", b"jpeg-data", "image/jpeg")
        )
        path, auth, request = FakeChatHandler.requests[0]
        self.assertEqual("/v1/chat/completions", path)
        self.assertEqual("Bearer test-key", auth)
        self.assertEqual("local-vlm", request["model"])
        self.assertEqual({"type": "json_object"}, request["response_format"])
        content = request["messages"][1]["content"]
        self.assertEqual("Task and Library", content[0]["text"])
        self.assertEqual(
            "data:image/jpeg;base64," + base64.b64encode(b"jpeg-data").decode(),
            content[1]["image_url"]["url"],
        )

    def test_missing_content_is_reported(self):
        FakeChatHandler.response = {"choices": [{"message": {"content": None}}]}
        model = OpenAICompatibleModel(f"http://127.0.0.1:{self.server.server_port}/v1", "local-vlm")
        with self.assertRaisesRegex(ModelAdapterError, "content"):
            model.generate("Task")

    def test_truncated_completion_is_rejected_with_raw_content(self):
        FakeChatHandler.response = {
            "choices": [{"finish_reason": "length", "message": {"content": '{"subgoals":[]}'}}]
        }
        model = OpenAICompatibleModel(f"http://127.0.0.1:{self.server.server_port}/v1", "local-vlm")
        with self.assertRaisesRegex(ModelAdapterError, "length") as caught:
            model.generate("Task")
        self.assertEqual('{"subgoals":[]}', caught.exception.raw_content)


if __name__ == "__main__":
    unittest.main()
