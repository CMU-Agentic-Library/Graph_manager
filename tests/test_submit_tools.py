"""The submit tool server speaks stdio MCP and validates plans inside the tool."""

import io
import json
import subprocess
import sys
import unittest

from graph_manager.adapters.submit_tools import ACCEPTED, call_tool, handle, serve
from graph_manager.adapters.zenobench_library import DEFAULT_ROOT, ZenoBenchLibrary
from graph_manager.prompts.task_plan import EXAMPLE_PLAN


def request(msg_id, method, params=None):
    return {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}


class SubmitToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def call(self, name, arguments):
        reply = handle(
            request(9, "tools/call", {"name": name, "arguments": arguments}), self.catalog
        )
        return reply["result"]

    def test_initialize_echoes_the_protocol_version(self):
        reply = handle(request(1, "initialize", {"protocolVersion": "2025-03-26"}), self.catalog)
        self.assertEqual("2025-03-26", reply["result"]["protocolVersion"])
        self.assertIn("tools", reply["result"]["capabilities"])

    def test_notifications_get_no_reply(self):
        message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.assertIsNone(handle(message, self.catalog))

    def test_tools_list_has_both_tools_with_their_schemas(self):
        tools = handle(request(2, "tools/list"), self.catalog)["result"]["tools"]
        self.assertEqual(["submit_plan", "submit_decision"], [tool["name"] for tool in tools])
        node = tools[0]["inputSchema"]["properties"]["subgraphs"]["items"]["properties"]["nodes"]
        self.assertIn("pick", node["items"]["properties"]["skill"]["enum"])
        self.assertEqual(
            ["continue", "finish"], tools[1]["inputSchema"]["properties"]["kind"]["enum"]
        )

    def test_valid_plan_is_accepted(self):
        result = self.call("submit_plan", EXAMPLE_PLAN)
        self.assertFalse(result["isError"])
        self.assertEqual(ACCEPTED, result["content"][0]["text"])

    def test_invalid_plan_returns_every_issue_as_a_tool_error(self):
        plan = json.loads(json.dumps(EXAMPLE_PLAN))
        plan["subgraphs"][0]["nodes"][1]["skill"] = "grab"

        result = self.call("submit_plan", plan)

        self.assertTrue(result["isError"])
        intro, errors = result["content"][0]["text"].split("\n", 1)
        self.assertIn("submit_plan again", intro)
        self.assertEqual(
            [("$.subgraphs[0].nodes[1].skill", "unknown_skill")],
            [(error["path"], error["code"]) for error in json.loads(errors)],
        )

    def test_decisions(self):
        self.assertEqual(
            (ACCEPTED, False), call_tool("submit_decision", {"kind": "finish"}, self.catalog)
        )
        self.assertTrue(call_tool("submit_decision", {"kind": "retry"}, self.catalog)[1])
        self.assertTrue(
            call_tool("submit_decision", {"kind": "finish", "why": "x"}, self.catalog)[1]
        )
        self.assertTrue(call_tool("no_such_tool", {}, self.catalog)[1])

    def test_unknown_method_is_a_jsonrpc_error(self):
        self.assertEqual(
            -32601, handle(request(5, "resources/list"), self.catalog)["error"]["code"]
        )

    def test_serve_answers_requests_line_by_line(self):
        messages = [
            request(1, "initialize"),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            request(2, "ping"),
        ]
        stdin = io.StringIO("".join(json.dumps(message) + "\n" for message in messages))
        stdout = io.StringIO()

        serve(stdin, stdout, self.catalog)

        self.assertEqual(
            [1, 2], [json.loads(line)["id"] for line in stdout.getvalue().splitlines()]
        )

    def test_module_runs_as_a_stdio_server(self):
        lines = "".join(
            json.dumps(m) + "\n" for m in (request(1, "initialize"), request(2, "tools/list"))
        )
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "graph_manager.adapters.submit_tools",
                "--zenobench-root",
                str(DEFAULT_ROOT),
            ],
            input=lines,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        replies = [json.loads(line) for line in done.stdout.splitlines()]
        self.assertEqual([1, 2], [reply["id"] for reply in replies])
        self.assertEqual(2, len(replies[1]["result"]["tools"]))

    def test_accepted_reply_tells_the_model_to_end_its_turn(self):
        self.assertIn("final for this turn", ACCEPTED)
        self.assertIn("End your turn now", ACCEPTED)


if __name__ == "__main__":
    unittest.main()
