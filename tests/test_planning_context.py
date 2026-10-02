"""Planning context and model failure behavior."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.openai_compatible import ModelAdapterError
from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.application.planning_loop import PlanningFailure, PlanningLoop
from graph_manager.domain.models import EntityCatalog, ObservedState, PlanningRequest

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")


def task_plan():
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
                        "skill_id": "skill_004",
                        "args": {"object": {"ref": "apple"}},
                        "depends_on": [],
                    }
                ],
            }
        ],
    }


class CapturingModel:
    def __init__(self, output):
        self.output = json.dumps(output)
        self.messages = None

    def generate(self, messages):
        self.messages = messages
        return self.output


class PlanningContextTest(unittest.TestCase):
    def test_optional_catalog_and_state_are_visible_when_provided(self):
        catalog = EntityCatalog.from_json(
            {"entities": [{"id": "apple", "types": ["MovableObject"]}]}
        )
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": True}]}
        )
        model = CapturingModel(task_plan())
        result = PlanningLoop(LIBRARY, model).run(
            PlanningRequest(
                "Hold apple", observation="Apple visible", entity_catalog=catalog, state=state
            )
        )
        self.assertTrue(result.grounded)
        prompt = model.messages[1].text
        self.assertIn("Apple visible", prompt)
        self.assertIn('"id": "apple"', prompt)
        self.assertIn("gripper_empty", prompt)

    def test_no_catalog_or_state_is_not_invented(self):
        model = CapturingModel(task_plan())
        result = PlanningLoop(LIBRARY, model).run(PlanningRequest("Hold apple"))
        self.assertFalse(result.grounded)
        prompt = model.messages[1].text
        self.assertNotIn("GT entity catalog", prompt)
        self.assertNotIn("Verified current state facts", prompt)

    def test_partial_model_output_is_saved_on_transport_failure(self):
        class TruncatedModel:
            def generate(self, _messages):
                raise ModelAdapterError("finish_reason=length", raw_content='{"partial":true}')

        with self.assertRaises(PlanningFailure) as caught:
            PlanningLoop(LIBRARY, TruncatedModel(), max_attempts=1).run(
                PlanningRequest("Hold apple")
            )
        self.assertEqual("model_output_incomplete", caught.exception.issues[0].code)
        self.assertEqual('{"partial":true}', caught.exception.attempts[0].raw_text)


if __name__ == "__main__":
    unittest.main()
