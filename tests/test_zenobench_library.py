"""The synced ZenoBench library exposes skill types, task IDs, and its commit."""

import re
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.skills import InputSpec, SkillCatalog, SkillSpec


class ZenoBenchLibraryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = ZenoBenchLibrary()
        cls.catalog = cls.library.load()

    def test_loads_every_synced_skill(self):
        self.assertEqual(70, len(self.catalog.skills))

    def test_resolves_by_verb_and_by_skill_id(self):
        pick = self.catalog.resolve("pick")
        self.assertEqual("skill_017", pick.skill_id)
        self.assertIs(pick, self.catalog.resolve("skill_017"))
        self.assertIsNone(self.catalog.resolve("grab"))

    def test_keeps_input_requirement_and_output_types(self):
        search = self.catalog.resolve("search")
        self.assertEqual(InputSpec("object_ref", True), search.inputs["object"])
        self.assertEqual(InputSpec("room_ref", False), search.inputs["region"])
        self.assertEqual("support_ref", search.outputs["found_on"])

    def test_task_ids_and_commit(self):
        self.assertEqual(35, len(self.library.task_ids()))
        self.assertIn("collect_fruits", self.library.task_ids())
        self.assertRegex(self.library.commit, re.compile(r"^[0-9a-f]{40}$"))
        self.assertTrue((self.library.skills_dir / "skill_017" / "SKILL.md").is_file())

    def test_duplicate_verbs_are_rejected(self):
        spec = SkillSpec("skill_001", "pick", {}, {})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            SkillCatalog((spec, SkillSpec("skill_002", "pick", {}, {})))

    def test_malformed_skill_json_is_a_value_error(self):
        with self.assertRaisesRegex(ValueError, "skill.json"):
            SkillSpec.from_json({"verb": "pick"})


if __name__ == "__main__":
    unittest.main()
