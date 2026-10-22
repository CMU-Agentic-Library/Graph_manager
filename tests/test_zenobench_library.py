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

    def test_task_index_and_commit(self):
        tasks = self.library.tasks()
        self.assertEqual(76, len(tasks))
        fruits = tasks["collect_fruits"]
        self.assertEqual(("gt", {"default": "easy"}), (fruits.default_profile, fruits.variants))
        book = tasks["T01_book_to_dining_table"]
        self.assertEqual("benchmark/v3/tasks.json", book.catalog)
        self.assertEqual("benchmark", book.default_profile)
        self.assertEqual("medium", book.variants["no_overhang"])
        self.assertRegex(self.library.commit, re.compile(r"^[0-9a-f]{40}$"))
        self.assertTrue((self.library.skills_dir / "skill_017" / "SKILL.md").is_file())

    def test_duplicate_verbs_are_rejected(self):
        spec = SkillSpec("skill_001", "pick", {}, {})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            SkillCatalog((spec, SkillSpec("skill_002", "pick", {}, {})))

    def test_malformed_skill_json_is_a_value_error(self):
        with self.assertRaisesRegex(ValueError, "skill.json"):
            SkillSpec.from_json({"verb": "pick"})

    def test_catalog_names_map_to_verbs_but_do_not_resolve(self):
        self.assertEqual("fetch", self.catalog.verb_for_name("fetch-object"))
        self.assertIsNone(self.catalog.verb_for_name("fetch"))
        self.assertIsNone(self.catalog.resolve("fetch-object"))

    def test_predicate_meanings_come_from_skill_conditions(self):
        meanings = self.library.predicate_meanings()
        self.assertEqual("The given gripper holds nothing.", meanings["hand_empty"])
        self.assertIn("holding", meanings)
        self.assertTrue(all(isinstance(text, str) and text for text in meanings.values()))


if __name__ == "__main__":
    unittest.main()
