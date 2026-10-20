"""A complete proposal is a list of Subgoals with one schema 2 subgraph each."""

import json
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.models import ProposalValidationError
from graph_manager.domain.task_plan import validate_task_plan


def subgraph(subgoal_id, *nodes):
    return {
        "schema_version": 2,
        "kind": "skill_subgraph",
        "subgoal_id": subgoal_id,
        "nodes": list(nodes),
    }


def pick(node_id="n1", target="apple"):
    return {"id": node_id, "skill": "pick", "args": {"object": {"ref": target}}, "depends_on": []}


def plan(subgoals=("sg_1", "sg_2"), graphs=None):
    if graphs is None:
        graphs = [subgraph(sid, pick()) for sid in subgoals]
    return {
        "schema_version": 2,
        "kind": "task_plan",
        "subgoals": [{"id": sid, "goal": f"goal of {sid}"} for sid in subgoals],
        "subgraphs": graphs,
    }


class TaskPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def issues(self, value):
        raw = value if isinstance(value, str) else json.dumps(value)
        with self.assertRaises(ProposalValidationError) as caught:
            validate_task_plan(raw, self.catalog)
        return [(issue.path, issue.code) for issue in caught.exception.issues]

    def test_valid_plan_is_returned(self):
        self.assertEqual(plan(), validate_task_plan(json.dumps(plan()), self.catalog))

    def test_json_syntax(self):
        self.assertEqual([("$", "json_syntax")], self.issues("{not json"))

    def test_envelope(self):
        value = plan()
        value["schema_version"] = 1
        value["kind"] = "plan"
        self.assertEqual(
            [("$.schema_version", "schema_version"), ("$.kind", "kind")], self.issues(value)
        )

    def test_every_subgoal_needs_exactly_one_subgraph(self):
        value = plan(
            graphs=[subgraph("sg_1", pick()), subgraph("sg_1", pick()), subgraph("sg_9", pick())]
        )
        self.assertEqual(
            [
                ("$.subgraphs[1].subgoal_id", "duplicate_subgraph"),
                ("$.subgraphs[2].subgoal_id", "unknown_subgoal"),
                ("$.subgraphs", "missing_subgraph"),
            ],
            self.issues(value),
        )

    def test_nested_issues_carry_the_subgraph_path(self):
        value = plan(
            graphs=[subgraph("sg_1", pick()), subgraph("sg_2", {**pick(), "skill": "grab"})]
        )
        self.assertEqual([("$.subgraphs[1].nodes[0].skill", "unknown_skill")], self.issues(value))

    def test_from_cannot_cross_subgoals(self):
        search = {
            "id": "n1",
            "skill": "search",
            "args": {"object": {"ref": "pot_lid"}},
            "depends_on": [],
        }
        navigate = {
            "id": "n2",
            "skill": "navigate",
            "args": {"destination": {"from": "n1.found_on"}},
            "depends_on": [],
        }
        value = plan(graphs=[subgraph("sg_1", search), subgraph("sg_2", navigate)])
        self.assertEqual(
            [("$.subgraphs[1].nodes[0].args.destination", "from_not_ancestor")], self.issues(value)
        )

    def test_subgoal_problems(self):
        value = plan()
        value["subgoals"] = [{"id": "sg_1", "goal": " "}, {"id": "sg_1", "goal": "again"}]
        self.assertEqual(
            [("$.subgoals[0].goal", "string_expected"), ("$.subgoals[1].id", "duplicate_id")],
            self.issues(value),
        )


if __name__ == "__main__":
    unittest.main()
