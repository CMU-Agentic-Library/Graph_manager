"""Tests for a complete model proposal and proven Contract conditions."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.domain.models import EntityCatalog, ObservedState, ProposalValidationError
from graph_manager.domain.task_plan_validation import validate_task_plan

ROOT = Path(__file__).resolve().parents[1]


def proposal(skill_id="skill_004", args=None):
    if args is None:
        args = {"object": {"ref": "apple"}}
    return {
        "schema_version": 1,
        "kind": "task_plan",
        "subgoals": [{"id": "sg_1", "goal": "Hold the apple"}],
        "subgraphs": [
            {
                "subgoal_id": "sg_1",
                "nodes": [{"id": "n1", "skill_id": skill_id, "args": args, "depends_on": []}],
            }
        ],
    }


class TaskPlanValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = JsonSkillLibraryRepository(
            ROOT / "skill_library" / "skill_library.json"
        ).load()

    def validate(self, value, state=None, catalog=None):
        return validate_task_plan(json.dumps(value), self.library, catalog, state)

    def test_valid_complete_plan_has_one_graph_per_subgoal(self):
        value = proposal()
        self.assertEqual(value, self.validate(value))

    def test_unknown_skill_error_points_to_exact_graph_node_field(self):
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(proposal(skill_id="skill_does_not_exist"))
        issue = caught.exception.issues[0]
        self.assertEqual("unknown_skill", issue.code)
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", issue.path)

    def test_missing_subgraph_points_to_subgraphs_array(self):
        value = proposal()
        value["subgraphs"] = []
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value)
        self.assertEqual("missing_subgraph", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs", caught.exception.issues[0].path)

    def test_zero_push_displacement_is_proven_precondition_failure(self):
        value = proposal(
            "skill_005",
            {
                "object": {"ref": "apple"},
                "displacement_xy": {"x": 0, "y": 0},
            },
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value)
        issue = caught.exception.issues[0]
        self.assertEqual("precondition_failed", issue.code)
        self.assertEqual("$.subgraphs[0].nodes[0].args.displacement_xy", issue.path)

    def test_independent_precondition_failures_are_reported_together(self):
        value = proposal(
            "skill_005",
            {"object": {"ref": "apple"}, "displacement_xy": {"x": 0, "y": 0}},
        )
        value["subgraphs"][0]["nodes"].append(
            {
                "id": "n2",
                "skill_id": "skill_005",
                "args": {"object": {"ref": "orange"}, "displacement_xy": {"x": 0, "y": 0}},
                "depends_on": [],
            }
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value)
        self.assertEqual(
            [
                "$.subgraphs[0].nodes[0].args.displacement_xy",
                "$.subgraphs[0].nodes[1].args.displacement_xy",
            ],
            [issue.path for issue in caught.exception.issues],
        )

    def test_known_false_initial_fact_rejects_ready_pick(self):
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": False}]}
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(proposal(), state=state)
        issue = caught.exception.issues[0]
        self.assertEqual("precondition_failed", issue.code)
        self.assertEqual("$.subgraphs[0].nodes[0]", issue.path)

    def test_unknown_fact_does_not_claim_failure(self):
        state = ObservedState.from_json({"facts": []})
        self.assertEqual(proposal(), self.validate(proposal(), state=state))

    def test_bound_holding_fact_rejects_ready_place(self):
        value = proposal(
            "skill_006",
            {"object": {"ref": "apple"}, "container": {"ref": "basket"}},
        )
        state = ObservedState.from_json(
            {
                "facts": [
                    {
                        "predicate": "holding",
                        "args": {"object": "apple"},
                        "value": False,
                    }
                ]
            }
        )
        catalog = EntityCatalog.from_json(
            {
                "entities": [
                    {"id": "apple", "types": ["MovableObject"]},
                    {"id": "basket", "types": ["ContainerObject"]},
                ]
            }
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value, state=state, catalog=catalog)
        self.assertEqual("precondition_failed", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes[0]", caught.exception.issues[0].path)

    def test_bound_fact_is_not_checked_without_grounded_catalog(self):
        value = proposal(
            "skill_006",
            {"object": {"ref": "apple"}, "container": {"ref": "basket"}},
        )
        state = ObservedState.from_json(
            {"facts": [{"predicate": "holding", "args": {"object": "apple"}, "value": False}]}
        )
        self.assertEqual(value, self.validate(value, state=state))

    def test_initial_fact_does_not_reject_later_dependent_node(self):
        value = proposal()
        value["subgraphs"][0]["nodes"].append(
            {
                "id": "n2",
                "skill_id": "skill_004",
                "args": {"object": {"ref": "orange"}},
                "depends_on": ["n1"],
            }
        )
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": True}]}
        )
        self.assertEqual(value, self.validate(value, state=state))

    def test_initial_state_is_not_applied_to_later_subgoal(self):
        value = proposal()
        value["subgoals"].append({"id": "sg_2", "goal": "Put apple in basket"})
        value["subgraphs"].append(
            {
                "subgoal_id": "sg_2",
                "nodes": [
                    {
                        "id": "n1",
                        "skill_id": "skill_006",
                        "args": {"object": {"ref": "apple"}, "container": {"ref": "basket"}},
                        "depends_on": [],
                    }
                ],
            }
        )
        state = ObservedState.from_json(
            {
                "facts": [
                    {"predicate": "gripper_empty", "args": {}, "value": True},
                    {"predicate": "holding", "args": {"object": "apple"}, "value": False},
                ]
            }
        )
        self.assertEqual(value, self.validate(value, state=state))

    def test_catalog_error_keeps_nested_path(self):
        catalog = EntityCatalog.from_json(
            {"entities": [{"id": "apple", "types": ["ContainerObject"]}]}
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(proposal(), catalog=catalog)
        self.assertEqual("entity_type", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes[0].args.object.ref", caught.exception.issues[0].path)

    def test_invalid_dependency_reports_its_position_before_duplicate_check(self):
        value = proposal()
        value["subgraphs"][0]["nodes"][0]["depends_on"] = [{}, {}]
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value)
        self.assertEqual("dependency_type", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes[0].depends_on[0]", caught.exception.issues[0].path)

    def test_cycle_error_points_into_containing_subgraph(self):
        value = proposal()
        value["subgraphs"][0]["nodes"][0]["depends_on"] = ["n2"]
        value["subgraphs"][0]["nodes"].append(
            {
                "id": "n2",
                "skill_id": "skill_004",
                "args": {"object": {"ref": "orange"}},
                "depends_on": ["n1"],
            }
        )
        with self.assertRaises(ProposalValidationError) as caught:
            self.validate(value)
        self.assertEqual("dependency_cycle", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes", caught.exception.issues[0].path)


if __name__ == "__main__":
    unittest.main()
