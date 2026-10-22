"""The executor turns one validated subgraph into ordered do_contract batches."""

import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.application.execution.graph_executor import GraphExecutor, plan_batches
from graph_manager.domain.env_types import ContractResult, ExecutionReply, Observation

OBSERVATION = Observation((), {})


def node(node_id, skill, args, depends_on=()):
    return {"id": node_id, "skill": skill, "args": args, "depends_on": list(depends_on)}


def graph(*nodes):
    return {
        "schema_version": 2,
        "kind": "skill_subgraph",
        "subgoal_id": "sg_1",
        "nodes": list(nodes),
    }


def result(call, success=True, outputs=None):
    return ContractResult(
        call.contract,
        call.args,
        success,
        None if success else "PRECONDITION_FAILED",
        None,
        (),
        (),
        outputs or {},
        None,
    )


class ScriptedEnvironment:
    """Test double for EnvironmentPort.do_contract: each reply is a function of the calls."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.batches = []

    def do_contract(self, exp_id, calls):
        self.batches.append([(c.contract, c.args) for c in calls])
        return ExecutionReply(exp_id, tuple(self.replies.pop(0)(calls)), OBSERVATION)


def all_succeed(calls):
    return [result(c) for c in calls]


class GraphExecutorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()

    def run_graph(self, environment, value):
        return GraphExecutor(environment, self.catalog).run("e1", value)

    def test_dependent_nodes_without_from_share_one_batch_and_use_verbs(self):
        environment = ScriptedEnvironment(all_succeed)
        run = self.run_graph(
            environment,
            graph(
                node("n1", "navigate", {"destination": {"ref": "apple"}}),
                node("n2", "skill_017", {"object": {"ref": "apple"}}, ["n1"]),
            ),
        )
        self.assertTrue(run.succeeded)
        self.assertEqual(
            [[("navigate", {"destination": "apple"}), ("pick", {"object": "apple"})]],
            environment.batches,
        )
        self.assertEqual(["n1", "n2"], [r.node_id for r in run.runs])
        self.assertIs(OBSERVATION, run.observation)

    def test_from_starts_a_new_batch_with_the_measured_output(self):
        environment = ScriptedEnvironment(
            lambda calls: [result(calls[0], outputs={"found_on": "kitchen_counter"})],
            all_succeed,
        )
        run = self.run_graph(
            environment,
            graph(
                node("n1", "search", {"object": {"ref": "pot_lid"}}),
                node("n2", "navigate", {"destination": {"from": "n1.found_on"}}, ["n1"]),
            ),
        )
        self.assertTrue(run.succeeded)
        self.assertEqual(
            [
                [("search", {"object": "pot_lid"})],
                [("navigate", {"destination": "kitchen_counter"})],
            ],
            environment.batches,
        )

    def test_first_failure_stops_the_graph(self):
        environment = ScriptedEnvironment(
            lambda calls: [result(calls[0]), result(calls[1], success=False)]
        )
        run = self.run_graph(
            environment,
            graph(
                node("n1", "navigate", {"destination": {"ref": "apple"}}),
                node("n2", "pick", {"object": {"ref": "apple"}}, ["n1"]),
                node("n3", "navigate", {"destination": {"ref": "basket"}}, ["n2"]),
                node("n4", "search", {"object": {"ref": "lid"}}),
                node("n5", "navigate", {"destination": {"from": "n4.found_on"}}, ["n4"]),
            ),
        )
        self.assertFalse(run.succeeded)
        self.assertEqual("n2", run.failed_node)
        self.assertEqual("contract_failed", run.failure)
        self.assertEqual(("n3", "n4", "n5"), run.not_run)
        self.assertEqual(1, len(environment.batches))

    def test_missing_output_stops_before_sending(self):
        environment = ScriptedEnvironment(all_succeed)
        run = self.run_graph(
            environment,
            graph(
                node("n1", "search", {"object": {"ref": "pot_lid"}}),
                node("n2", "navigate", {"destination": {"from": "n1.found_on"}}, ["n1"]),
            ),
        )
        self.assertEqual("n2", run.failed_node)
        self.assertEqual("output_missing", run.failure)
        self.assertEqual(("n2",), run.not_run)
        self.assertEqual(1, len(environment.batches))

    def test_plan_batches(self):
        nodes = [
            node("a", "search", {"object": {"ref": "x"}}),
            node("b", "pick", {"object": {"ref": "y"}}),
            node("c", "navigate", {"destination": {"from": "a.found_on"}}, ["a"]),
            node("d", "pick", {"object": {"ref": "z"}}, ["c"]),
        ]
        self.assertEqual(
            [["a", "b"], ["c", "d"]], [[n["id"] for n in batch] for batch in plan_batches(nodes)]
        )


if __name__ == "__main__":
    unittest.main()
