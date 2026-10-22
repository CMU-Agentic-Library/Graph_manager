"""Closed-loop prompts report what happened and never reveal the evaluator's status."""

import json
import unittest

from graph_manager.application.execution.graph_executor import GraphRun, NodeRun
from graph_manager.domain.env_types import (
    CameraImage,
    ContractResult,
    Observation,
    SceneObject,
    TaskInfo,
)
from graph_manager.domain.models import ValidationIssue
from graph_manager.prompts.episode import (
    decision_feedback,
    episode_start_text,
    observation_text,
    subgoal_feedback_text,
)

OBSERVATION = Observation(
    (CameraImage("head", b"h"), CameraImage("left_wrist", b"l"), CameraImage("right_wrist", b"r")),
    (SceneObject("apple", "object", (2.9, 5.6, 0.9)),),
    {"base_pose": [2.4, 5.6, 15.0], "held_right": "orange", "held_left": None},
    ({"atom": "inside(apple, fruit_basket)", "holds": False},),
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
        self.assertIn("- apple (object) at [2.9, 5.6, 0.9]", text)
        self.assertIn("Right hand holds: orange; left hand holds: nothing", text)
        self.assertIn("head, left_wrist, right_wrist", text)
        self.assertNotIn("fruit_basket", text)

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
        self.assertNotIn('Reply with {"kind": "continue"}', text)
        self.assertNotIn("inside(apple, fruit_basket)", text)

    def test_success_report_offers_continue(self):
        run = GraphRun((NodeRun("n1", OK),), (), None, None, OBSERVATION)
        text = subgoal_feedback_text(
            {"id": "a", "goal": "A"}, run, OBSERVATION, MEANINGS, [{"id": "b", "goal": "B"}], None
        )
        self.assertIn('Reply with {"kind": "continue"}', text)

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
        self.assertIn('Reply with {"kind": "continue"} if the remaining plan still fits', text)
        start = episode_start_text(TaskInfo("t", "t", "Do it."), OBSERVATION)
        self.assertIn("send a task_plan only to change the remaining work", start)


if __name__ == "__main__":
    unittest.main()
