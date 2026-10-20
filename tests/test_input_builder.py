"""Model-visible turns carry the task and observation, never the skill library itself."""

import json
import unittest

from graph_manager.application.input_builder import PlanningInputBuilder
from graph_manager.domain.models import ImageInput, PlanningRequest, ValidationIssue


class PlanningInputBuilderTest(unittest.TestCase):
    def test_initial_turn_has_instructions_goal_observation_and_image(self):
        request = PlanningRequest(
            "Hold apple",
            image=b"image-bytes",
            image_mime="image/png",
            observation="Apple on the table",
        )

        turn = PlanningInputBuilder().initial(request)

        self.assertIn("Return exactly one JSON object", turn.text)
        self.assertIn("schema_version=2", turn.text)
        self.assertIn("Hold apple", turn.text)
        self.assertIn("Apple on the table", turn.text)
        self.assertIn("A current scene image is attached.", turn.text)
        self.assertNotIn("skill.json", turn.text)
        self.assertEqual((ImageInput(b"image-bytes", "image/png"),), turn.images)

    def test_absent_optional_sources_are_not_invented(self):
        turn = PlanningInputBuilder().initial(PlanningRequest("Hold apple"))

        self.assertNotIn("Current observation", turn.text)
        self.assertNotIn("image is attached", turn.text)
        self.assertEqual((), turn.images)

    def test_feedback_turn_contains_only_errors_and_no_image(self):
        issue = ValidationIssue("$.subgraphs[0].nodes[0].skill", "unknown_skill", "unknown")

        turn = PlanningInputBuilder().feedback((issue,))

        self.assertEqual((), turn.images)
        body = json.loads(turn.text)
        self.assertEqual("validation_feedback", body["kind"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill", body["errors"][0]["path"])

    def test_instructions_explain_verbs_and_show_an_example(self):
        text = PlanningInputBuilder().initial(PlanningRequest("Hold apple")).text

        self.assertIn('"skill": "fetch"', text)
        self.assertIn("not the catalog name", text)
        self.assertIn('{"ref": "mug"}', text)
        self.assertIn("no markdown code fences", text)


if __name__ == "__main__":
    unittest.main()
