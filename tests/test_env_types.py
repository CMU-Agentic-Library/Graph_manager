"""Environment replies parse into typed records; malformed ones raise ValueError."""

import copy
import unittest

from graph_manager.domain.env_types import (
    ContractCall,
    ExecutionReply,
    ExpStatus,
    GoalCheck,
    StartedTask,
    TaskRequest,
)
from graph_manager.ports import EnvironmentPortError

PNG_B64 = "iVBORw0KGgo="  # the 8-byte PNG signature
OBSERVATION = {
    "images": [{"camera": "head", "png_base64": PNG_B64}],
    "objects": [{"name": "apple", "kind": "object", "position": [2.93, 5.61, 0.89]}],
    "robot": {"base_pose": [2.45, 5.62, 15.0], "held_right": None, "held_left": None},
    "task_status": [{"atom": "inside(apple, fruit_basket)", "holds": False}],
}
GT_PROFILE = {
    "name": "gt",
    "observation": ["images", "objects", "robot", "task_status"],
    "max_calls": 40,
}
BOOK = {
    "name": "paperback_book",
    "category": "paperback_book",
    "tags": ["book", "flat"],
    "in_view": True,
    "held": False,
    "last_seen_position": [7.62, 1.55, 0.92],
    "last_seen_on": "kitchen_island/top",
    "last_seen_in": None,
    "last_seen_tick": 1340,
}
BENCHMARK_OBSERVATION = {
    "images": [{"camera": "head", "png_base64": PNG_B64}],
    "visible_objects": [BOOK],
    "observation_cache": [BOOK],
    "known_places": {"kitchen": {"kind": "room"}},
    "robot": {"held_right": None, "held_left": None, "room": "kitchen", "temperatures_c": {}},
    "last_result": None,
}
TASK = {
    "task_id": "collect_fruits",
    "name": "collect_fruits",
    "description": "Collect both fruits.",
}
FAILED_PICK = {
    "contract": "pick",
    "args": {"object": "apple"},
    "success": False,
    "error_code": "PRECONDITION_FAILED",
    "error": "reachable(target=apple) is false",
    "preconditions": [{"atom": "reachable(target=apple)", "holds": False}],
    "postconditions": [],
    "outputs": {},
}


class EnvTypesTest(unittest.TestCase):
    def test_started_task(self):
        started = StartedTask.from_json(
            {
                "exp_id": "collect_fruits-1a2b",
                "task": TASK,
                "profile": GT_PROFILE,
                "observation": OBSERVATION,
            }
        )
        self.assertEqual("collect_fruits-1a2b", started.exp_id)
        self.assertEqual("collect_fruits", started.task.task_id)
        self.assertEqual(("gt", 40), (started.profile.name, started.profile.max_calls))
        self.assertEqual(b"\x89PNG\r\n\x1a\n", started.observation.images[0].png)
        self.assertEqual("apple", started.observation.fields["objects"][0]["name"])
        self.assertNotIn("images", started.observation.fields)
        self.assertEqual("inside(apple, fruit_basket)", started.observation.task_status[0]["atom"])

    def test_benchmark_observation_keeps_the_fields_it_has(self):
        started = StartedTask.from_json(
            {
                "exp_id": "e",
                "task": TASK,
                "profile": {
                    "name": "benchmark",
                    "observation": list(BENCHMARK_OBSERVATION),
                    "max_calls": 60,
                },
                "observation": BENCHMARK_OBSERVATION,
            }
        )
        observation = started.observation
        self.assertEqual((), observation.task_status)
        self.assertNotIn("objects", observation.fields)
        self.assertEqual(
            "kitchen_island/top", observation.fields["visible_objects"][0]["last_seen_on"]
        )

    def test_started_task_needs_every_field_the_profile_lists(self):
        profile = dict(GT_PROFILE, observation=["images", "objects", "visible_objects"])
        with self.assertRaisesRegex(ValueError, "visible_objects"):
            StartedTask.from_json(
                {"exp_id": "e", "task": TASK, "profile": profile, "observation": OBSERVATION}
            )
        with self.assertRaisesRegex(ValueError, "profile"):
            StartedTask.from_json({"exp_id": "e", "task": TASK, "observation": OBSERVATION})

    def test_task_request_json_and_path(self):
        request = TaskRequest("T01", profile="benchmark", variant="no_overhang", seed=10)
        self.assertEqual(
            {"task_id": "T01", "seed": 10, "profile": "benchmark", "variant": "no_overhang"},
            request.to_json(),
        )
        self.assertEqual("T01/benchmark/no_overhang/seed_10", str(request.path))
        self.assertEqual(
            "T01/gt/difficulty-hard/seed_0",
            str(TaskRequest("T01", profile="gt", difficulty="hard").path),
        )
        self.assertEqual("T01/catalog-default/any/seed_0", str(TaskRequest("T01").path))
        with self.assertRaisesRegex(ValueError, "not both"):
            TaskRequest("T01", variant="a", difficulty="easy")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            TaskRequest(" ")

    def test_execution_reply_keeps_contract_failure_details(self):
        reply = ExecutionReply.from_json(
            {"exp_id": "e", "results": [FAILED_PICK], "observation": OBSERVATION}
        )
        result = reply.results[0]
        self.assertFalse(result.success)
        self.assertEqual("PRECONDITION_FAILED", result.error_code)
        self.assertEqual("reachable(target=apple)", result.preconditions[0]["atom"])
        self.assertIsNone(result.failed_step)

    def test_goal_check_and_exp_status(self):
        check = GoalCheck.from_json(
            {
                "exp_id": "e",
                "success": True,
                "goal": [{"atom": "inside(apple, b)", "holds": True}],
                "dropped": [],
                "episode": {"variant": "default", "seed": 0},
            }
        )
        self.assertTrue(check.success)
        self.assertEqual(((), "default"), (check.dropped, check.episode["variant"]))
        running = ExpStatus.from_json(
            {"exp_id": "e", "state": "running", "calls_used": 3, "observation": None}
        )
        self.assertIsNone(running.observation)
        with self.assertRaisesRegex(ValueError, "state"):
            ExpStatus.from_json({"exp_id": "e", "state": "busy", "calls_used": 0})

    def test_malformed_replies(self):
        bad_image = copy.deepcopy(OBSERVATION)
        bad_image["images"][0]["png_base64"] = "not base64!"
        bad_success = dict(FAILED_PICK, success="no")
        with self.assertRaises(ValueError):
            ExecutionReply.from_json({"exp_id": "e", "results": [], "observation": bad_image})
        with self.assertRaises(ValueError):
            ExecutionReply.from_json(
                {"exp_id": "e", "results": [bad_success], "observation": OBSERVATION}
            )

    def test_contract_call_json(self):
        self.assertEqual(
            {"contract": "pick", "args": {"object": "apple"}},
            ContractCall("pick", {"object": "apple"}).to_json(),
        )

    def test_port_error_knows_when_the_exp_is_gone(self):
        self.assertTrue(
            EnvironmentPortError("x", error_code="EXP_RELEASED", http_status=410).exp_gone
        )
        self.assertTrue(
            EnvironmentPortError("x", error_code="SIM_CRASHED", http_status=500).exp_gone
        )
        self.assertFalse(EnvironmentPortError("x", error_code="CLIENT_TIMEOUT").exp_gone)


if __name__ == "__main__":
    unittest.main()
