import json
import tempfile
import unittest
from pathlib import Path

from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository


class RepositoryTest(unittest.TestCase):
    def test_rejects_skill_missing_id_with_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "types": {"MovableObject": "object"},
                        "skills": [{"inputs": {"object": "MovableObject"}}],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "invalid Skill"):
                JsonSkillLibraryRepository(path).load()

    def test_rejects_private_top_level_fields_in_model_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "types": {},
                        "skills": [],
                        "executor": {"path": "private.py"},
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "private field"):
                JsonSkillLibraryRepository(path).load()

    def test_rejects_private_executor_fields_in_model_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "types": {"MovableObject": "object"},
                        "skills": [
                            {
                                "id": "skill_x",
                                "inputs": {"object": "MovableObject"},
                                "executor": {"callable": "private.function"},
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "private field"):
                JsonSkillLibraryRepository(path).load()

    def test_rejects_malformed_checkable_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "types": {"MovableObject": "object"},
                        "skills": [
                            {
                                "id": "skill_001",
                                "inputs": {"object": "MovableObject"},
                                "checkable_requires": {"kind": "fact"},
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "checkable_requires"):
                JsonSkillLibraryRepository(path).load()

    def test_rejects_fact_bound_to_nonentity_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "types": {"OptionalVector2": "vector"},
                        "skills": [
                            {
                                "id": "skill_001",
                                "inputs": {"hint": "OptionalVector2"},
                                "checkable_requires": [
                                    {
                                        "kind": "fact",
                                        "predicate": "holding",
                                        "args": {"object": "hint"},
                                    }
                                ],
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "invalid fact"):
                JsonSkillLibraryRepository(path).load()


if __name__ == "__main__":
    unittest.main()
