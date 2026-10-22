"""The planning service owns task policy, not SDK conversation storage."""

import json
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.application.errors import PlanningFailure
from graph_manager.application.planning_service import PlanningService
from graph_manager.domain.models import ImageInput, PlanningRequest
from graph_manager.ports import ModelPortError

LIBRARY = ZenoBenchLibrary()


def proposal(skill="pick"):
    return {
        "schema_version": 2,
        "kind": "task_plan",
        "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
        "subgraphs": [
            {
                "schema_version": 2,
                "kind": "skill_subgraph",
                "subgoal_id": "sg_1",
                "nodes": [
                    {
                        "id": "n1",
                        "skill": skill,
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

    def ask(self, text, images=()):
        self.turns.append((text, images))
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return json.dumps(output) if isinstance(output, dict) else output


class PlanningServiceTest(unittest.TestCase):
    def test_valid_plan_uses_one_turn_and_preserves_image(self):
        session = ScriptedSession([proposal()])

        result = PlanningService(LIBRARY, session).run(
            PlanningRequest("Hold apple", image=b"pixels", image_mime="image/png")
        )

        self.assertEqual(proposal(), result.task_plan)
        self.assertEqual("statically_validated", result.to_json()["status"])
        self.assertEqual((ImageInput(b"pixels", "image/png"),), session.turns[0][1])

    def test_invalid_skill_sends_only_feedback_as_second_turn(self):
        session = ScriptedSession([proposal("grab"), proposal()])

        result = PlanningService(LIBRARY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual(2, len(result.attempts))
        self.assertEqual((), session.turns[1][1])
        feedback = json.loads(session.turns[1][0])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill", feedback["errors"][0]["path"])

    def test_invalid_json_generates_feedback_in_same_session(self):
        session = ScriptedSession(["{not-json", proposal()])

        result = PlanningService(LIBRARY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual("json_syntax", json.loads(session.turns[1][0])["errors"][0]["code"])
        self.assertEqual(2, len(result.attempts))

    def test_incomplete_model_turn_is_recorded_and_repaired(self):
        session = ScriptedSession(
            [ModelPortError("max-tokens", partial_output='{"partial":'), proposal()]
        )

        result = PlanningService(LIBRARY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual('{"partial":', result.attempts[0].raw_text)
        self.assertEqual("model_output_incomplete", result.attempts[0].issues[0].code)

    def test_rejects_after_bounded_attempts(self):
        session = ScriptedSession([proposal("grab")])

        with self.assertRaises(PlanningFailure) as caught:
            PlanningService(LIBRARY, session, max_attempts=1).run(PlanningRequest("Hold apple"))

        self.assertEqual("unknown_skill", caught.exception.issues[0].code)
        self.assertEqual(2, caught.exception.to_json()["schema_version"])

    def test_five_attempts_by_default(self):
        self.assertEqual(5, PlanningService(LIBRARY, ScriptedSession([])).max_attempts)


if __name__ == "__main__":
    unittest.main()
