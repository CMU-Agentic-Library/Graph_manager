"""The HTTP client sends interface v3 requests and maps every failure to one error type."""

import io
import json
import unittest
import urllib.error

from graph_manager.adapters.env_http import HttpEnvironment
from graph_manager.domain.env_types import ContractCall, TaskRequest
from graph_manager.ports import EnvironmentPortError

OBSERVATION = {"images": [], "objects": [], "robot": {}, "task_status": []}
PROFILE = {
    "name": "gt",
    "observation": ["images", "objects", "robot", "task_status"],
    "max_calls": 40,
}


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


class Recorder:
    """Stands in for urllib.request.urlopen and returns or raises scripted outcomes."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        payload = outcome if isinstance(outcome, bytes) else json.dumps(outcome).encode()
        return FakeResponse(payload)

    def body(self, index=0):
        return json.loads(self.requests[index][0].data)


def http_error(status, payload):
    return urllib.error.HTTPError("http://env/x", status, "error", {}, io.BytesIO(payload))


class HttpEnvironmentTest(unittest.TestCase):
    def test_initial_task_request_and_reply(self):
        recorder = Recorder(
            {
                "exp_id": "e1",
                "task": {"task_id": "collect_fruits", "name": "collect_fruits", "description": "d"},
                "profile": PROFILE,
                "observation": OBSERVATION,
            }
        )
        started = HttpEnvironment("http://env:8800/", urlopen=recorder).initial_task(
            TaskRequest("collect_fruits", profile="gt", seed=3)
        )

        request, timeout = recorder.requests[0]
        self.assertEqual("http://env:8800/initial_task", request.full_url)
        self.assertEqual("POST", request.get_method())
        self.assertEqual({"task_id": "collect_fruits", "profile": "gt", "seed": 3}, recorder.body())
        self.assertEqual(900, timeout)
        self.assertEqual("e1", started.exp_id)

    def test_do_contract_sends_the_batch(self):
        recorder = Recorder({"exp_id": "e1", "results": [], "observation": OBSERVATION})
        HttpEnvironment("http://env", urlopen=recorder).do_contract(
            "e1",
            [
                ContractCall("navigate", {"destination": "apple"}),
                ContractCall("pick", {"object": "apple"}),
            ],
        )
        self.assertEqual(
            {
                "exp_id": "e1",
                "calls": [
                    {"contract": "navigate", "args": {"destination": "apple"}},
                    {"contract": "pick", "args": {"object": "apple"}},
                ],
            },
            recorder.body(),
        )
        self.assertEqual(1800, recorder.requests[0][1])

    def test_check_task_and_observe(self):
        recorder = Recorder(
            {"exp_id": "e1", "success": False, "goal": [], "dropped": [], "episode": {}},
            {"exp_id": "e1", "state": "ready", "calls_used": 4, "observation": OBSERVATION},
        )
        environment = HttpEnvironment("http://env", urlopen=recorder)
        self.assertFalse(environment.check_task("e1").success)
        self.assertEqual(4, environment.observe("e1").calls_used)
        self.assertEqual("http://env/observe", recorder.requests[1][0].full_url)
        self.assertEqual(60, recorder.requests[1][1])

    def test_service_error_keeps_status_and_code(self):
        recorder = Recorder(http_error(410, b'{"error_code": "EXP_RELEASED", "error": "idle"}'))
        with self.assertRaises(EnvironmentPortError) as caught:
            HttpEnvironment("http://env", urlopen=recorder).check_task("e1")
        self.assertEqual(410, caught.exception.http_status)
        self.assertEqual("EXP_RELEASED", caught.exception.error_code)
        self.assertTrue(caught.exception.exp_gone)

    def test_error_without_json_body(self):
        recorder = Recorder(http_error(502, b"<html>bad gateway</html>"))
        with self.assertRaises(EnvironmentPortError) as caught:
            HttpEnvironment("http://env", urlopen=recorder).check_task("e1")
        self.assertEqual("HTTP_ERROR", caught.exception.error_code)

    def test_client_timeout_and_transport_failure(self):
        cases = [
            (TimeoutError("timed out"), "CLIENT_TIMEOUT"),
            (urllib.error.URLError(TimeoutError("timed out")), "CLIENT_TIMEOUT"),
            (urllib.error.URLError("connection refused"), "TRANSPORT_ERROR"),
        ]
        for failure, code in cases:
            with self.subTest(code=code), self.assertRaises(EnvironmentPortError) as caught:
                HttpEnvironment("http://env", urlopen=Recorder(failure)).observe("e1")
            self.assertEqual(code, caught.exception.error_code)

    def test_unexpected_reply_is_bad_response(self):
        for payload in (b"not json", b"[]", b'{"exp_id": "e1"}'):
            with self.subTest(payload=payload), self.assertRaises(EnvironmentPortError) as caught:
                HttpEnvironment("http://env", urlopen=Recorder(payload)).check_task("e1")
            self.assertEqual("BAD_RESPONSE", caught.exception.error_code)

    def test_arguments_are_checked_before_sending(self):
        environment = HttpEnvironment("http://env", urlopen=Recorder())
        with self.assertRaisesRegex(ValueError, "calls"):
            environment.do_contract("e1", [])
        with self.assertRaisesRegex(ValueError, "http"):
            HttpEnvironment("env:8800")


if __name__ == "__main__":
    unittest.main()
