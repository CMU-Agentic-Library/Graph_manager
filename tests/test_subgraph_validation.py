"""Schema 2 subgraph checks mirror ZenoBench graph.py and report every issue."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.subgraph import topological_order, validate_subgraph

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "zenobench_plans"


def node(node_id, skill, args, depends_on=()):
    return {"id": node_id, "skill": skill, "args": args, "depends_on": list(depends_on)}


def graph(*nodes):
    return {
        "schema_version": 2,
        "kind": "skill_subgraph",
        "subgoal_id": "sg_1",
        "nodes": list(nodes),
    }


class SubgraphValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def codes(self, value):
        return [(issue.path, issue.code) for issue in validate_subgraph(value, self.catalog)]

    def test_every_zenobench_reference_plan_is_valid(self):
        paths = sorted(FIXTURES.glob("*.skill_subgraph.json"))
        self.assertEqual(35, len(paths))
        for path in paths:
            with self.subTest(plan=path.name):
                self.assertEqual([], self.codes(json.loads(path.read_text())))

    def test_verb_or_skill_id_names_a_skill(self):
        self.assertEqual(
            [], self.codes(graph(node("n1", "skill_017", {"object": {"ref": "apple"}})))
        )
        self.assertEqual(
            [("$.nodes[0].skill", "unknown_skill")],
            self.codes(graph(node("n1", "grab", {"object": {"ref": "apple"}}))),
        )

    def test_reports_every_input_problem_in_one_pass(self):
        value = graph(
            node("n1", "navigate", {"speed": {"value": 1}}),
            node("n2", "retreat", {"obstacle": {"ref": "table"}, "distance_m": {"ref": "far"}}),
            node("n3", "retreat", {"obstacle": {"ref": "table"}, "distance_m": {"value": -1}}),
            node("n4", "pick", {"object": {"ref": "apple", "value": "apple"}}),
        )
        self.assertEqual(
            [
                ("$.nodes[0].args.destination", "missing_input"),
                ("$.nodes[0].args.speed", "unknown_input"),
                ("$.nodes[1].args.distance_m", "ref_not_allowed"),
                ("$.nodes[2].args.distance_m", "invalid_value"),
                ("$.nodes[3].args.object", "arg_form"),
            ],
            self.codes(value),
        )

    def test_from_reads_a_compatible_output_of_an_ancestor(self):
        value = graph(
            node("n1", "search", {"object": {"ref": "pot_lid"}}),
            node("n2", "navigate", {"destination": {"from": "n1.found_on"}}, ["n1"]),
        )
        self.assertEqual([], self.codes(value))

    def test_from_problems(self):
        value = graph(
            node("n1", "search", {"object": {"ref": "pot_lid"}}),
            node("n2", "navigate", {"destination": {"from": "n1.found_on"}}),
            node("n3", "navigate", {"destination": {"from": "n1.nowhere"}}, ["n1"]),
            node("n4", "navigate", {"destination": {"from": "n1.visited"}}, ["n1"]),
            node("n5", "navigate", {"destination": {"from": "n1"}}, ["n1"]),
        )
        self.assertEqual(
            [
                ("$.nodes[4].args.destination", "from_syntax"),
                ("$.nodes[1].args.destination", "from_not_ancestor"),
                ("$.nodes[2].args.destination", "unknown_output"),
                ("$.nodes[3].args.destination", "output_type"),
            ],
            self.codes(value),
        )

    def test_dependency_problems(self):
        pick = {"object": {"ref": "apple"}}
        self.assertEqual(
            [("$.nodes[0].depends_on", "bad_dependency")],
            self.codes(graph(node("n1", "pick", pick, ["n9"]))),
        )
        self.assertEqual(
            [("$.nodes", "cycle")],
            self.codes(graph(node("n1", "pick", pick, ["n2"]), node("n2", "pick", pick, ["n1"]))),
        )
        self.assertEqual(
            [("$.nodes[1].id", "duplicate_id")],
            self.codes(graph(node("n1", "pick", pick), node("n1", "pick", pick))),
        )

    def test_envelope_problems_use_the_given_path(self):
        issues = validate_subgraph(
            {"schema_version": 1, "kind": "x", "subgoal_id": "9", "nodes": []},
            self.catalog,
            "$.subgraphs[2]",
        )
        self.assertEqual(
            [
                ("$.subgraphs[2].schema_version", "schema_version"),
                ("$.subgraphs[2].kind", "kind"),
                ("$.subgraphs[2].subgoal_id", "identifier"),
                ("$.subgraphs[2].nodes", "nodes"),
            ],
            [(issue.path, issue.code) for issue in issues],
        )

    def test_topological_order_is_stable(self):
        nodes = [node("a", "pick", {}, ["b"]), node("b", "pick", {}), node("c", "pick", {})]
        self.assertEqual(["b", "a", "c"], [n["id"] for n in topological_order(nodes)])

    def test_unknown_skill_message_names_the_verb_for_a_catalog_name(self):
        value = graph(node("n1", "fetch-object", {"object": {"ref": "apple"}}))
        (issue,) = validate_subgraph(value, self.catalog)
        self.assertEqual("unknown_skill", issue.code)
        self.assertIn("'fetch'", issue.message)

    def test_object_list_takes_a_value_list_of_scene_names(self):
        args = {"objects": {"value": ["apple", "orange"]}, "container": {"ref": "fruit_basket"}}
        self.assertEqual([], self.codes(graph(node("n1", "collect", args))))

    def test_form_errors_show_the_form_for_the_input_type(self):
        basket = {"ref": "fruit_basket"}
        value = graph(
            node("n1", "collect", {"objects": [{"ref": "apple"}], "container": basket}),
            node("n2", "collect", {"objects": {"ref": "apple"}, "container": basket}),
            node("n3", "pick", {"object": "apple"}),
        )
        issues = validate_subgraph(value, self.catalog)
        self.assertEqual(["arg_form", "ref_not_allowed", "arg_form"], [i.code for i in issues])
        self.assertIn('"objects": {"value": ["apple", "orange"]}', issues[0].message)
        self.assertIn('"objects": {"value": ["apple", "orange"]}', issues[1].message)
        self.assertIn('"object": {"ref": "apple"}', issues[2].message)


if __name__ == "__main__":
    unittest.main()
