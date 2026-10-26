"""Closed-loop prompts report what happened and never reveal the evaluator's status."""

import json
import unittest

from graph_manager.application.execution.graph_executor import GraphRun, NodeRun
from graph_manager.domain.env_types import (
    CameraImage,
    ContractResult,
    Observation,
    TaskInfo,
)
from graph_manager.domain.models import ValidationIssue
from graph_manager.prompts.episode import (
    call_report,
    decision_feedback,
    episode_start_text,
    observation_text,
    subgoal_feedback_text,
)

OBSERVATION = Observation(
    (CameraImage("head", b"h"), CameraImage("left_wrist", b"l"), CameraImage("right_wrist", b"r")),
    {
        "objects": [{"name": "apple", "kind": "object", "position": [2.9, 5.6, 0.9]}],
        "robot": {"base_pose": [2.4, 5.6, 15.0], "held_right": "orange", "held_left": None},
        "task_status": [{"atom": "inside(apple, fruit_basket)", "holds": False}],
    },
)
BOOK = {
    "name": "paperback_book",
    "category": "book",
    "in_view": True,
    "held": False,
    "last_seen_position": [7.62, 1.55, 0.92],
    "last_seen_on": "kitchen_island/top",
    "last_seen_in": None,
}
MUG = dict(
    BOOK, name="mug", category="mug", in_view=False, last_seen_on=None, last_seen_in="cabinet_1"
)
BENCHMARK = Observation(
    (CameraImage("head", b"h"),),
    {
        "visible_objects": [BOOK],
        "observation_cache": [BOOK, MUG],
        "known_places": {
            "kitchen": {"kind": "room"},
            "kitchen_island/top": {"kind": "support", "room": "kitchen", "center": [7.6, 1.5]},
            "fridge/door_button": {"kind": "button", "appliance": "fridge"},
        },
        "robot": {
            "held_right": None,
            "held_left": None,
            "room": "kitchen",
            "temperatures_c": {"tomato": 4.0},
        },
        "last_result": {"contract": "look", "args": {"object": "secret_last_result"}},
        "weather": {"rain": True},
    },
)
FAILED = ContractResult(
    "pick",
    {"object": "apple"},
    False,
    "PRECONDITION_FAILED",
    "hand_empty(hand=right) is false",
    (
        {"atom": "hand_empty(hand=right)", "holds": False},
        {"atom": "base_near(place=apple)", "holds": True},
    ),
    (),
    {},
    None,
)
OK = ContractResult(
    "navigate", {"destination": "apple"}, True, None, None, (), (), {"arrived": True}, None
)
MEANINGS = {"hand_empty": "The given gripper holds nothing."}


class EpisodePromptTest(unittest.TestCase):
    def test_observation_text_lists_objects_and_robot_but_not_task_status(self):
        text = observation_text(OBSERVATION)
        self.assertIn("- apple (object)", text)
        self.assertNotIn("2.9", text)
        self.assertIn("Right hand holds: orange; left hand holds: nothing", text)
        self.assertIn("head, left_wrist, right_wrist", text)
        self.assertNotIn("fruit_basket", text)

    def test_benchmark_observation_text(self):
        text = observation_text(BENCHMARK)
        self.assertIn("Objects in view now", text)
        self.assertIn("- paperback_book (book), on kitchen_island/top", text)
        self.assertIn("- mug (mug), in cabinet_1", text)
        self.assertEqual(1, text.count("paperback_book"))
        self.assertIn("- kitchen: kitchen_island/top (support)", text)
        self.assertIn("- no room given: fridge/door_button (button)", text)
        self.assertIn("Robot is in room: kitchen", text)
        self.assertIn("tomato 4.0", text)
        self.assertIn('weather: {"rain":true}', text)
        self.assertNotIn("secret_last_result", text)
        self.assertNotIn("7.6", text)

    def test_new_error_codes_explain_how_to_recover(self):
        result = ContractResult(
            "pick", {"object": "mug"}, False, "NOT_IN_VIEW", "mug", (), (), {}, None
        )
        report = call_report(NodeRun("n1", result), {})
        self.assertIn("look", report["meaning"])

    def test_start_text_has_rules_task_and_observation(self):
        text = episode_start_text(
            TaskInfo("collect_fruits", "collect_fruits", "Collect fruits."), OBSERVATION
        )
        self.assertIn("schema_version=2", text)
        self.assertIn('{"kind": "continue"}', text)
        self.assertIn("Collect fruits.", text)
        self.assertNotIn("inside(apple, fruit_basket)", text)

    def test_failed_subgoal_report_explains_the_error_and_conditions(self):
        run = GraphRun(
            (NodeRun("n1", OK), NodeRun("n2", FAILED)),
            ("n3",),
            "n2",
            "contract_failed",
            OBSERVATION,
        )
        text = subgoal_feedback_text(
            {"id": "hold_apple", "goal": "Hold the apple"},
            run,
            OBSERVATION,
            MEANINGS,
            [{"id": "hold_apple", "goal": "Hold the apple"}],
            "The subgoal failed.",
        )
        report = json.loads(text.split("\n\n", 1)[0])
        self.assertEqual("failed", report["status"])
        self.assertEqual({"arrived": True}, report["calls"][0]["outputs"])
        failed = report["calls"][1]
        self.assertEqual("PRECONDITION_FAILED", failed["error_code"])
        self.assertIn("robot did not move", failed["meaning"])
        self.assertEqual(
            [{"atom": "hand_empty(hand=right)", "meaning": "The given gripper holds nothing."}],
            failed["false_conditions"],
        )
        self.assertEqual(["n3"], report["not_run"])
        self.assertIn("Remaining planned subgoals: hold_apple (Hold the apple)", text)
        self.assertIn("The subgoal failed.", text)
        self.assertNotIn('"kind": "continue"', text)
        self.assertNotIn("inside(apple, fruit_basket)", text)

    def test_success_report_offers_continue(self):
        run = GraphRun((NodeRun("n1", OK),), (), None, None, OBSERVATION)
        text = subgoal_feedback_text(
            {"id": "a", "goal": "A"}, run, OBSERVATION, MEANINGS, [{"id": "b", "goal": "B"}], None
        )
        self.assertIn('mcp__graph__submit_decision with {"kind": "continue"}', text)

    def test_decision_feedback_lists_errors(self):
        body = json.loads(decision_feedback((ValidationIssue("$.kind", "kind", "bad"),)))
        self.assertEqual("validation_feedback", body["kind"])
        self.assertEqual("kind", body["errors"][0]["code"])
        self.assertIn("finish", body["instruction"])

    def test_continue_is_the_reply_when_the_remaining_plan_still_fits(self):
        run = GraphRun((NodeRun("n1", OK),), (), None, None, OBSERVATION)
        text = subgoal_feedback_text(
            {"id": "a", "goal": "A"}, run, OBSERVATION, MEANINGS, [{"id": "b", "goal": "B"}], None
        )
        self.assertIn('with {"kind": "continue"} if the remaining plan still fits', text)
        start = episode_start_text(TaskInfo("t", "t", "Do it."), OBSERVATION)
        self.assertIn("send a task_plan only to change the remaining work", start)

    def test_every_turn_asks_for_a_tool_call(self):
        start = episode_start_text(TaskInfo("t", "t", "Do it."), OBSERVATION)
        self.assertIn("mcp__graph__submit_plan", start)
        self.assertIn("mcp__graph__submit_decision", start)
        self.assertTrue(
            start.endswith("Submit the complete task_plan now with mcp__graph__submit_plan.")
        )
        body = json.loads(decision_feedback((ValidationIssue("$.kind", "kind", "bad"),)))
        self.assertIn("mcp__graph__submit_decision", body["instruction"])


if __name__ == "__main__":
    unittest.main()
