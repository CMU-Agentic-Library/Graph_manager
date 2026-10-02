"""The planning application keeps one conversation across corrective turns."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.openai_compatible import ModelAdapterError
from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.application.planning_loop import PlanningFailure, PlanningLoop
from graph_manager.domain.models import ObservedState, PlanningRequest

ROOT = Path(__file__).resolve().parents[1]


def plan(skill_id="skill_004"):
    return {
        "schema_version": 1,
        "kind": "task_plan",
        "subgoals": [{"id": "sg_1", "goal": "Hold the apple"}],
        "subgraphs": [
            {
                "subgoal_id": "sg_1",
                "nodes": [
                    {
                        "id": "n1",
                        "skill_id": skill_id,
                        "args": {"object": {"ref": "apple"}},
                        "depends_on": [],
                    }
                ],
            }
        ],
    }


class SequenceModel:
    def __init__(self, outputs):
        self.outputs = iter(
            json.dumps(item) if isinstance(item, dict) else item for item in outputs
        )
        self.calls = []

    def generate(self, messages):
        self.calls.append(tuple(messages))
        return next(self.outputs)


class PlanningLoopTest(unittest.TestCase):
    def loop(self, model, max_attempts=3):
        repository = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")
        return PlanningLoop(repository, model, max_attempts=max_attempts)

    def test_valid_first_response_uses_one_model_call(self):
        model = SequenceModel([plan()])
        result = self.loop(model).run(PlanningRequest("Hold the apple", image=b"jpeg"))
        self.assertEqual(plan(), result.task_plan)
        self.assertEqual(1, len(model.calls))
        self.assertEqual(2, len(model.calls[0]))
        self.assertEqual(b"jpeg", model.calls[0][1].image)
        self.assertEqual("unresolved_references", result.to_json()["status"])

    def test_invalid_skill_feedback_reuses_context_and_points_to_field(self):
        invalid = plan("made_up_skill")
        model = SequenceModel([invalid, plan()])
        result = self.loop(model).run(PlanningRequest("Hold the apple"))
        self.assertEqual(2, len(model.calls))
        first, second = model.calls
        self.assertEqual(first, second[:2])
        self.assertIn("Hold the apple", second[1].text)
        self.assertIn("skill_009", second[1].text)
        self.assertEqual(json.dumps(invalid), second[2].text)
        self.assertEqual("assistant", second[2].role)
        self.assertEqual("user", second[3].role)
        feedback = json.loads(second[3].text)
        self.assertEqual("validation_feedback", feedback["kind"])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", feedback["errors"][0]["path"])
        self.assertEqual(2, len(result.attempts))

    def test_invalid_json_is_returned_as_corrective_input(self):
        model = SequenceModel(["{not json", plan()])
        self.loop(model).run(PlanningRequest("Hold apple"))
        feedback = json.loads(model.calls[1][-1].text)
        self.assertEqual("json_syntax", feedback["errors"][0]["code"])
        self.assertEqual("$", feedback["errors"][0]["path"])

    def test_proven_precondition_failure_is_returned_as_feedback(self):
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": False}]}
        )
        model = SequenceModel([plan(), plan()])
        with self.assertRaises(PlanningFailure) as caught:
            self.loop(model, max_attempts=2).run(PlanningRequest("Hold apple", state=state))
        self.assertEqual(2, len(model.calls))
        feedback = json.loads(model.calls[1][-1].text)
        self.assertEqual("precondition_failed", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0]", feedback["errors"][0]["path"])
        self.assertEqual("rejected", caught.exception.to_json()["status"])

    def test_feedback_includes_all_independent_precondition_failures(self):
        invalid = plan()
        invalid["subgraphs"][0]["nodes"] = [
            {
                "id": node_id,
                "skill_id": "skill_005",
                "args": {"object": {"ref": object_id}, "displacement_xy": {"x": 0, "y": 0}},
                "depends_on": [],
            }
            for node_id, object_id in (("n1", "apple"), ("n2", "orange"))
        ]
        model = SequenceModel([invalid, plan()])
        self.loop(model).run(PlanningRequest("Hold apple"))
        feedback = json.loads(model.calls[1][-1].text)
        self.assertEqual(
            [
                "$.subgraphs[0].nodes[0].args.displacement_xy",
                "$.subgraphs[0].nodes[1].args.displacement_xy",
            ],
            [error["path"] for error in feedback["errors"]],
        )

    def test_retry_limit_preserves_last_errors_and_attempts(self):
        model = SequenceModel([plan("bad_1"), plan("bad_2")])
        with self.assertRaises(PlanningFailure) as caught:
            self.loop(model, max_attempts=2).run(PlanningRequest("Hold apple"))
        self.assertEqual(2, len(model.calls))
        self.assertEqual(2, len(caught.exception.attempts))
        self.assertEqual("unknown_skill", caught.exception.issues[0].code)

    def test_truncated_response_becomes_feedback_and_can_recover(self):
        class PartialThenValid:
            def __init__(self):
                self.calls = []

            def generate(self, messages):
                self.calls.append(messages)
                if len(self.calls) == 1:
                    raise ModelAdapterError("finish_reason=length", raw_content='{"partial":')
                return json.dumps(plan())

        model = PartialThenValid()
        result = self.loop(model).run(PlanningRequest("Hold apple"))
        self.assertEqual(plan(), result.task_plan)
        self.assertEqual(2, len(model.calls))
        self.assertEqual('{"partial":', model.calls[1][-2].text)
        feedback = json.loads(model.calls[1][-1].text)
        self.assertEqual("model_output_incomplete", feedback["errors"][0]["code"])


if __name__ == "__main__":
    unittest.main()
