"""A planning request carries a Goal and optional observation inputs."""

import unittest

from graph_manager.domain.models import PlanningRequest


class PlanningRequestTest(unittest.TestCase):
    def test_goal_is_required(self):
        with self.assertRaisesRegex(ValueError, "goal"):
            PlanningRequest(" ")

    def test_image_must_be_nonempty_and_a_supported_type(self):
        with self.assertRaisesRegex(ValueError, "image"):
            PlanningRequest("Hold apple", image=b"")
        with self.assertRaisesRegex(ValueError, "image_mime"):
            PlanningRequest("Hold apple", image=b"x", image_mime="image/gif")


if __name__ == "__main__":
    unittest.main()
