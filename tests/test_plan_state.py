"""A plan is checked against what the hands hold, with the synced skills' conditions."""

import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.plan_state import hand_issues

EMPTY = {"held_right": None, "held_left": None}


def node(node_id, skill, depends_on=(), **args):
    return {
        "id": node_id,
        "skill": skill,
        "args": {name: {"ref": value} for name, value in args.items()},
        "depends_on": list(depends_on),
    }


def plan(*subgoals):
    """subgoals: (id, [nodes]) in order."""
    return {
        "schema_version": 2,
        "kind": "task_plan",
        "subgoals": [{"id": sid, "goal": sid} for sid, _ in subgoals],
        "subgraphs": [
            {"schema_version": 2, "kind": "skill_subgraph", "subgoal_id": sid, "nodes": nodes}
            for sid, nodes in subgoals
        ],
    }


class HandIssuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def issues(self, the_plan, robot=EMPTY):
        return hand_issues(the_plan, self.catalog, robot)

    def test_pick_then_place_then_pick_is_fine(self):
        the_plan = plan(
            (
                "move",
                [
                    node("n1", "pick", object="apple"),
                    node("n2", "place", ["n1"], object="apple", receptacle="table/top"),
                    node("n3", "pick", ["n2"], object="orange"),
                ],
            )
        )
        self.assertEqual([], self.issues(the_plan))

    def test_pick_while_holding_something_now(self):
        the_plan = plan(("get_mug", [node("n1", "pick", object="mug")]))

        (issue,) = self.issues(the_plan, {"held_right": "wooden_block_b", "held_left": None})

        self.assertEqual("hand_not_empty", issue.code)
        self.assertEqual("$.subgraphs[0].nodes[0].skill", issue.path)
        self.assertIn("right hand will still hold wooden_block_b (it holds it now)", issue.message)

    def test_a_held_object_carries_over_to_the_next_subgoal(self):
        the_plan = plan(
            ("first", [node("n1", "pick", object="apple")]),
            ("second", [node("n2", "pick", object="orange")]),
        )

        (issue,) = self.issues(the_plan)

        self.assertEqual("$.subgraphs[1].nodes[0].skill", issue.path)
        self.assertIn("node n1 leaves it there", issue.message)

    def test_place_without_holding_the_object(self):
        the_plan = plan(("put", [node("n1", "place", object="apple", receptacle="table/top")]))

        (issue,) = self.issues(the_plan, {"held_right": "orange", "held_left": None})

        self.assertEqual("hand_not_holding", issue.code)
        self.assertIn("needs the right hand to hold apple", issue.message)
        self.assertIn("holds orange", issue.message)

    def test_handover_moves_the_object_to_the_left_hand(self):
        the_plan = plan(
            (
                "swap_hands",
                [
                    node("n1", "pick", object="apple"),
                    node("n2", "handover", ["n1"], object="apple"),
                    node("n3", "pick", ["n2"], object="orange"),
                ],
            )
        )
        self.assertEqual([], self.issues(the_plan))
        the_plan["subgraphs"][0]["nodes"].append(node("n4", "handover", ["n3"], object="orange"))
        (issue,) = self.issues(the_plan)
        self.assertIn("needs an empty left hand", issue.message)

    def test_a_precondition_shared_by_every_path_is_checked(self):
        the_plan = plan(("open_it", [node("n1", "open", articulated="kitchen_microwave")]))

        (issue,) = self.issues(the_plan, {"held_right": "soda_can", "held_left": None})

        self.assertEqual("hand_not_empty", issue.code)

    def test_nodes_follow_depends_on_not_list_order(self):
        the_plan = plan(
            (
                "move",
                [
                    node("n2", "place", ["n1"], object="apple", receptacle="table/top"),
                    node("n1", "pick", object="apple"),
                ],
            )
        )
        self.assertEqual([], self.issues(the_plan))


if __name__ == "__main__":
    unittest.main()
