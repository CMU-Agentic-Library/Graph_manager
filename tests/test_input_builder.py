"""Model-visible turns are built before they reach the Harness adapter."""

import json
import unittest

from graph_manager.application.input_builder import PlanningInputBuilder
from graph_manager.domain.models import (
    EntityCatalog,
    ObservedState,
    PlanningRequest,
    ValidationIssue,
)


class PlanningInputBuilderTest(unittest.TestCase):
    def test_initial_turn_contains_public_context_and_original_image(self):
        catalog = EntityCatalog.from_json(
            {"entities": [{"id": "apple", "types": ["MovableObject"]}]}
        )
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": True}]}
        )
        request = PlanningRequest(
            "Hold apple",
            image=b"image-bytes",
            image_mime="image/png",
            observation="Apple visible",
            entity_catalog=catalog,
            state=state,
        )
        library = {"version": 1, "skills": [{"id": "skill_004"}], "types": {}}

        turn = PlanningInputBuilder().initial(request, library)

        self.assertIn("Return exactly one JSON object", turn.text)
        self.assertIn("Hold apple", turn.text)
        self.assertIn("Apple visible", turn.text)
        self.assertIn('"id": "skill_004"', turn.text)
        self.assertIn('"id": "apple"', turn.text)
        self.assertIn("gripper_empty", turn.text)
        self.assertEqual(b"image-bytes", turn.image)
        self.assertEqual("image/png", turn.image_mime)

    def test_absent_optional_sources_are_not_invented(self):
        library = {"version": 1, "skills": [], "types": {}}

        turn = PlanningInputBuilder().initial(PlanningRequest("Hold apple"), library)

        self.assertNotIn("GT entity catalog (use exact IDs", turn.text)
        self.assertNotIn("Verified current state facts", turn.text)
        self.assertIsNone(turn.image)

    def test_feedback_turn_contains_only_errors_and_no_image(self):
        issue = ValidationIssue(
            "$.subgraphs[0].nodes[0].skill_id", "unknown_skill", "unknown Skill ID"
        )

        turn = PlanningInputBuilder().feedback((issue,))

        self.assertIsNone(turn.image)
        self.assertEqual("image/jpeg", turn.image_mime)
        body = json.loads(turn.text)
        self.assertEqual("validation_feedback", body["kind"])
        self.assertEqual("unknown_skill", body["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", body["errors"][0]["path"])


if __name__ == "__main__":
    unittest.main()
