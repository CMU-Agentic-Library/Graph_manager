import json
import unittest
from pathlib import Path

from graph_manager.domain import EntityCatalog, ProposalValidationError
from graph_manager.validation import (
    validate_complete_plan,
    validate_skill_subgraph,
    validate_subgoal_plan,
)

LIBRARY = json.loads(
    (Path(__file__).resolve().parents[1] / "skill_library" / "skill_library.json").read_text()
)
CATALOG = EntityCatalog.from_json(
    {
        "entities": [
            {"id": "apple", "types": ["MovableObject"]},
            {"id": "basket", "types": ["MovableObject", "ContainerObject"]},
        ]
    }
)
SUBGOALS = {
    "schema_version": 1,
    "kind": "subgoal_plan",
    "subgoals": [
        {"id": "sg_1", "goal": "Apple is in the basket"},
        {"id": "sg_2", "goal": "Basket is on the bookcase"},
    ],
}
GRAPH = {
    "schema_version": 1,
    "kind": "skill_subgraph",
    "subgoal_id": "sg_1",
    "nodes": [
        {
            "id": "n1",
            "skill_id": "skill_004",
            "args": {"object": {"ref": "apple"}},
            "depends_on": [],
        },
        {
            "id": "n2",
            "skill_id": "skill_006",
            "args": {"object": {"ref": "apple"}, "container": {"ref": "basket"}},
            "depends_on": ["n1"],
        },
    ],
}


class ProposalValidationTest(unittest.TestCase):
    def assert_issue(self, proposal, code, path="", catalog=CATALOG):
        with self.assertRaises(ProposalValidationError) as caught:
            validate_skill_subgraph(json.dumps(proposal), {"sg_1", "sg_2"}, LIBRARY, catalog)
        self.assertTrue(
            any(
                issue.code == code and (not path or issue.path == path)
                for issue in caught.exception.issues
            ),
            caught.exception.issues,
        )

    def test_valid_plan_and_graph_and_complete_coverage(self):
        plan = validate_subgoal_plan(json.dumps(SUBGOALS))
        first = validate_skill_subgraph(json.dumps(GRAPH), {"sg_1", "sg_2"}, LIBRARY, CATALOG)
        second = validate_skill_subgraph(
            json.dumps(
                {
                    **GRAPH,
                    "subgoal_id": "sg_2",
                    "nodes": [
                        {
                            "id": "n1",
                            "skill_id": "skill_004",
                            "args": {"object": {"ref": "basket"}},
                            "depends_on": [],
                        },
                    ],
                }
            ),
            {"sg_1", "sg_2"},
            LIBRARY,
            CATALOG,
        )
        self.assertEqual("sg_1", first["subgoal_id"])
        validate_complete_plan(plan, [first, second])

    def test_malformed_json_and_duplicate_subgoals_have_paths(self):
        with self.assertRaises(ProposalValidationError) as caught:
            validate_subgoal_plan("{bad")
        self.assertEqual("json_syntax", caught.exception.issues[0].code)
        duplicate = {**SUBGOALS, "subgoals": [SUBGOALS["subgoals"][0]] * 2}
        with self.assertRaises(ProposalValidationError) as caught:
            validate_subgoal_plan(json.dumps(duplicate))
        self.assertEqual("$.subgoals[1].id", caught.exception.issues[0].path)

    def test_duplicate_json_keys_are_rejected(self):
        raw = '{"schema_version":1,"kind":"subgoal_plan","kind":"skill_subgraph","subgoals":[]}'
        with self.assertRaises(ProposalValidationError) as caught:
            validate_subgoal_plan(raw)
        self.assertEqual("json_syntax", caught.exception.issues[0].code)

    def test_unknown_skill_and_argument_names(self):
        changed = json.loads(json.dumps(GRAPH))
        changed["nodes"][0]["skill_id"] = "skill_999"
        self.assert_issue(changed, "unknown_skill", "$.nodes[0].skill_id")
        changed["nodes"][0]["skill_id"] = "skill_004"
        changed["nodes"][0]["args"] = {"wrong": {"ref": "apple"}}
        self.assert_issue(changed, "argument_names", "$.nodes[0].args")

    def test_catalog_exact_id_and_type(self):
        changed = json.loads(json.dumps(GRAPH))
        changed["nodes"][1]["args"]["container"] = {"ref": "apple"}
        self.assert_issue(changed, "entity_type", "$.nodes[1].args.container.ref")
        changed["nodes"][1]["args"]["container"] = {"ref": "missing"}
        self.assert_issue(changed, "unknown_entity", "$.nodes[1].args.container.ref")

    def test_absent_catalog_accepts_unresolved_ref_and_empty_catalog_does_not(self):
        changed = json.loads(json.dumps(GRAPH))
        changed["nodes"][0]["args"]["object"] = {"ref": "the red fruit"}
        validate_skill_subgraph(json.dumps(changed), {"sg_1"}, LIBRARY, None)
        self.assert_issue(
            changed,
            "unknown_entity",
            "$.nodes[0].args.object.ref",
            EntityCatalog.from_json({"entities": []}),
        )

    def test_pose_and_optional_vector_are_checked(self):
        graph = {
            **GRAPH,
            "nodes": [
                {
                    "id": "n1",
                    "skill_id": "skill_001",
                    "args": {"target_pose": {"x": 1, "y": False, "yaw_deg": 90}},
                    "depends_on": [],
                }
            ],
        }
        self.assert_issue(graph, "argument_type", "$.nodes[0].args.target_pose.y")
        graph["nodes"][0] = {
            "id": "n1",
            "skill_id": "skill_007",
            "args": {"object": {"ref": "apple"}, "support": {"ref": "shelf"}},
            "depends_on": [],
        }
        self.assert_issue(graph, "argument_names", "$.nodes[0].args")

    def test_dangling_dependency_and_cycle(self):
        changed = json.loads(json.dumps(GRAPH))
        changed["nodes"][1]["depends_on"] = ["absent"]
        self.assert_issue(changed, "unknown_dependency", "$.nodes[1].depends_on[0]")
        changed["nodes"][1]["depends_on"] = ["n1"]
        changed["nodes"][0]["depends_on"] = ["n2"]
        self.assert_issue(changed, "dependency_cycle", "$.nodes")

    def test_long_acyclic_chain_does_not_hit_python_recursion_limit(self):
        nodes = [
            {
                "id": f"n{index}",
                "skill_id": "skill_004",
                "args": {"object": {"ref": "apple"}},
                "depends_on": [f"n{index - 1}"] if index else [],
            }
            for index in range(1100)
        ]
        nodes.reverse()
        graph = {**GRAPH, "nodes": nodes}
        self.assertEqual(
            1100,
            len(validate_skill_subgraph(json.dumps(graph), {"sg_1"}, LIBRARY, CATALOG)["nodes"]),
        )

    def test_wrong_subgoal_and_missing_graph(self):
        self.assert_issue({**GRAPH, "subgoal_id": "sg_other"}, "unknown_subgoal", "$.subgoal_id")
        with self.assertRaises(ProposalValidationError) as caught:
            validate_complete_plan(validate_subgoal_plan(json.dumps(SUBGOALS)), [GRAPH])
        self.assertEqual("missing_subgraph", caught.exception.issues[0].code)


if __name__ == "__main__":
    unittest.main()
