import json
import tempfile
import unittest
from pathlib import Path

from skill_library.build import build


ROOT = Path(__file__).resolve().parents[1] / "skill_library"


class SkillLibraryTest(unittest.TestCase):
    def test_aggregate_matches_every_contract_and_saved_json(self):
        sources = sorted((ROOT / "skills").glob("skill_*.json"))
        self.assertEqual([f"skill_{number:03}.json" for number in range(1, 10)],
                         [source.name for source in sources])
        contracts = [json.loads(path.read_text()) for path in sources]
        result = build(ROOT)

        self.assertEqual([contract["id"] for contract in contracts],
                         [skill["id"] for skill in result["skills"]])
        self.assertEqual(sum(len(contract.get("connections", [])) for contract in contracts),
                         len(result["connections"]))
        self.assertEqual(result, json.loads((ROOT / "skill_library.json").read_text()))

    def test_public_projection_is_model_facing(self):
        result = build(ROOT)
        self.assertTrue(result["skills"])
        for skill in result["skills"]:
            self.assertTrue({"id", "name", "description", "inputs", "requires",
                             "achieves", "outcomes"} <= skill.keys())
            self.assertNotIn("executor", skill)
            self.assertNotIn("verifier", skill)
            self.assertNotIn("source_function", skill)
            self.assertNotIn("selectable", skill)
            self.assertNotIn("kind", skill)
        self.assertNotIn("zeno_skills", json.dumps(result))

    def test_builder_validates_ids_types_and_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skills").mkdir()
            (root / "types.json").write_text(json.dumps({"types": {"Target": "description"}}))
            contract = {
                "id": "skill_a", "name": "A", "description": "Do A",
                "inputs": {"target": "Target"}, "requires": [], "achieves": [],
                "outcomes": {"success": "yes", "failure": "no"},
                "executor": {"callable": "a"}, "verifier": {"available": "none"},
                "connections": [{"to": ["skill_b"], "when": "after A"}],
            }
            first = root / "skills" / "skill_001.json"
            second = root / "skills" / "skill_002.json"
            first.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "unknown connection target"):
                build(root)

            second.write_text(json.dumps({**contract, "id": "skill_b", "connections": []}))
            self.assertEqual(["skill_a", "skill_b"],
                             [skill["id"] for skill in build(root)["skills"]])

            second.write_text(json.dumps({**contract, "connections": []}))
            with self.assertRaisesRegex(ValueError, "Duplicate skill ID"):
                build(root)

            second.write_text(json.dumps({**contract, "id": "skill_b", "inputs": {"target": "Unknown"}, "connections": []}))
            with self.assertRaisesRegex(ValueError, "unknown input types"):
                build(root)

            second.write_text(json.dumps({**contract, "id": "skill_b", "inputs": {"target": "Target"},
                                          "source_function": {"file": "private.py"}, "connections": []}))
            self.assertNotIn("source_function", build(root)["skills"][1])


if __name__ == "__main__":
    unittest.main()
