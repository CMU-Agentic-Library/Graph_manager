"""A planning request carries a Goal and optional observation inputs."""

import unittest

from graph_manager.domain.models import ImageInput, PlanningRequest


class PlanningRequestTest(unittest.TestCase):
    def test_goal_is_required(self):
        with self.assertRaisesRegex(ValueError, "goal"):
            PlanningRequest(" ")

    def test_image_must_be_nonempty_and_a_supported_type(self):
        with self.assertRaisesRegex(ValueError, "image"):
            PlanningRequest("Hold apple", image=b"")
        with self.assertRaisesRegex(ValueError, "image_mime"):
            PlanningRequest("Hold apple", image=b"x", image_mime="image/gif")

    def test_image_input_checks_data_and_type(self):
        self.assertEqual("image/png", ImageInput(b"x").mime)
        with self.assertRaisesRegex(ValueError, "nonempty"):
            ImageInput(b"")
        with self.assertRaisesRegex(ValueError, "mime"):
            ImageInput(b"x", "image/gif")


if __name__ == "__main__":
    unittest.main()
