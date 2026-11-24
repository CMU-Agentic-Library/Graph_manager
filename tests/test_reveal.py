"""SHIFT_REVEAL: off by default (prompts unchanged); on, the vendored ZenoBench card's facts
for observed kinds (and, in full, surface uses) reach the observation text."""

import os
import unittest
from unittest import mock

from graph_manager.domain.env_types import Observation
from graph_manager.prompts import episode, reveal

FIELDS = {
    "visible_objects": [
        {
            "name": "breakfast_plate_1",
            "category": "breakfast_plate",
            "last_seen_on": "kitchen_counter_2/top",
        }
    ],
    "observation_cache": [
        {
            "name": "handled_cooking_pot_1",
            "category": "handled_cooking_pot",
            "last_seen_on": "kitchen_stove/top",
        }
    ],
    "known_places": {
        "dining_room_0_0": {"kind": "room"},
        "dining_table_1/top": {"kind": "support", "room": "dining_room_0_0"},
    },
}


def text(mode: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "SHIFT_REVEAL"}
    if mode is not None:
        env["SHIFT_REVEAL"] = mode
    with mock.patch.dict(os.environ, env, clear=True):
        return episode.observation_text(Observation(fields=FIELDS, images=()))


class RevealTest(unittest.TestCase):
    def test_off_by_default(self):
        self.assertEqual(text(None), text("off"))
        self.assertNotIn("Object facts", text(None))

    def test_objects(self):
        out = text("objects")
        self.assertIn(reveal.card()["objects"]["breakfast_plate"], out)
        self.assertIn(reveal.card()["objects"]["handled_cooking_pot"], out)
        self.assertNotIn("breakfast_bowl", out)
        self.assertIn("dining_table_1/top (support)", out)

    def test_full_tags_surfaces(self):
        tags = reveal.card()["surfaces"]["dining_table_1/top"]
        self.assertIn(f"dining_table_1/top (support: {tags})", text("full"))

    def test_bad_mode(self):
        with mock.patch.dict(os.environ, {"SHIFT_REVEAL": "everything"}):
            with self.assertRaises(ValueError):
                reveal.mode()


if __name__ == "__main__":
    unittest.main()
