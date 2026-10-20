"""After a subgoal the model continues, replans the remaining work, or finishes."""

import json
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.decision import validate_decision
from graph_manager.domain.models import ProposalValidationError

PLAN = {
    "schema_version": 2,
    "kind": "task_plan",
    "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
    "subgraphs": [
        {
            "schema_version": 2,
            "kind": "skill_subgraph",
            "subgoal_id": "sg_1",
            "nodes": [
                {
                    "id": "n1",
                    "skill": "pick",
                    "args": {"object": {"ref": "apple"}},
                    "depends_on": [],
                }
            ],
        }
    ],
}


class DecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def decide(self, value, blocked=None):
        return validate_decision(json.dumps(value), self.catalog, blocked)

    def issues(self, value, blocked=None):
        with self.assertRaises(ProposalValidationError) as caught:
            self.decide(value, blocked)
        return [(issue.path, issue.code, issue.message) for issue in caught.exception.issues]

    def test_the_three_kinds(self):
        self.assertEqual("continue", self.decide({"kind": "continue"}).kind)
        self.assertEqual("finish", self.decide({"kind": "finish"}).kind)
        decision = self.decide(PLAN)
        self.assertEqual("task_plan", decision.kind)
        self.assertEqual(PLAN, decision.plan)

    def test_continue_can_be_blocked_with_a_reason(self):
        self.assertEqual(
            [("$.kind", "continue_not_allowed", "The subgoal failed.")],
            self.issues({"kind": "continue"}, "The subgoal failed."),
        )
        self.assertEqual("finish", self.decide({"kind": "finish"}, "The subgoal failed.").kind)

    def test_invalid_replies(self):
        self.assertEqual("kind", self.issues({"kind": "retry"})[0][1])
        self.assertEqual("field_names", self.issues({"kind": "finish", "why": "done"})[0][1])
        bad_plan = json.loads(json.dumps(PLAN))
        bad_plan["subgraphs"][0]["nodes"][0]["skill"] = "grab"
        self.assertEqual(
            [("$.subgraphs[0].nodes[0].skill", "unknown_skill")],
            [issue[:2] for issue in self.issues(bad_plan)],
        )

    def test_reply_must_be_json(self):
        with self.assertRaises(ProposalValidationError) as caught:
            validate_decision("continue", self.catalog)
        self.assertEqual("json_syntax", caught.exception.issues[0].code)


if __name__ == "__main__":
    unittest.main()
