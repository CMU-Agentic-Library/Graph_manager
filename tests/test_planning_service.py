"""The planning service owns task policy, not SDK conversation storage."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.application.errors import PlanningFailure
from graph_manager.application.planning_service import PlanningService
from graph_manager.domain.models import ObservedState, PlanningRequest
from graph_manager.ports import ModelPortError

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")


def proposal(skill_id="skill_004"):
    return {
        "schema_version": 1,
        "kind": "task_plan",
        "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
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


class ScriptedSession:
    session_id = "test-session"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.turns = []

    def ask(self, text, image=None, image_mime="image/jpeg"):
        self.turns.append((text, image, image_mime))
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return json.dumps(output) if isinstance(output, dict) else output


class PlanningServiceTest(unittest.TestCase):
    def test_valid_plan_uses_one_turn_and_preserves_image(self):
        session = ScriptedSession([proposal()])

        result = PlanningService(REPOSITORY, session).run(
            PlanningRequest("Hold apple", image=b"pixels", image_mime="image/png")
        )

        self.assertEqual(proposal(), result.task_plan)
        self.assertEqual(1, len(result.attempts))
        self.assertEqual("unresolved_references", result.to_json()["status"])
        self.assertEqual(b"pixels", session.turns[0][1])
        self.assertEqual("image/png", session.turns[0][2])

    def test_invalid_skill_sends_only_feedback_as_second_turn(self):
        session = ScriptedSession([proposal("invented_skill"), proposal()])

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual(2, len(result.attempts))
        self.assertEqual(2, len(session.turns))
        self.assertIn("Complete public Skill Library JSON", session.turns[0][0])
        self.assertNotIn("Complete public Skill Library JSON", session.turns[1][0])
        self.assertIsNone(session.turns[1][1])
        feedback = json.loads(session.turns[1][0])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", feedback["errors"][0]["path"])

    def test_invalid_json_generates_feedback_in_same_session(self):
        session = ScriptedSession(["{not-json", proposal()])

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual(2, len(result.attempts))
        self.assertEqual("json_syntax", json.loads(session.turns[1][0])["errors"][0]["code"])

    def test_incomplete_model_turn_is_recorded_and_repaired(self):
        session = ScriptedSession(
            [ModelPortError("max-tokens", partial_output='{"partial":'), proposal()]
        )

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual('{"partial":', result.attempts[0].raw_text)
        self.assertEqual("model_output_incomplete", result.attempts[0].issues[0].code)
        self.assertEqual(
            "model_output_incomplete",
            json.loads(session.turns[1][0])["errors"][0]["code"],
        )

    def test_known_false_initial_fact_rejects_after_limit(self):
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": False}]}
        )
        session = ScriptedSession([proposal()])

        with self.assertRaises(PlanningFailure) as caught:
            PlanningService(REPOSITORY, session, max_attempts=1).run(
                PlanningRequest("Hold apple", state=state)
            )

        self.assertEqual("precondition_failed", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes[0]", caught.exception.issues[0].path)
        self.assertEqual(1, len(caught.exception.attempts))


if __name__ == "__main__":
    unittest.main()
