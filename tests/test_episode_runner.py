"""One task runs as a closed loop: plan, execute a subgoal, report, decide."""

import itertools
import json
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.application.orchestration.episode_runner import (
    ALL_DONE,
    EpisodeLimits,
    EpisodeRunner,
)
from graph_manager.application.orchestration.trajectory import MemoryRecorder
from graph_manager.domain.env_types import (
    CameraImage,
    ContractResult,
    ExecutionReply,
    GoalCheck,
    Observation,
    SceneObject,
    StartedTask,
    TaskInfo,
)
from graph_manager.ports import EnvironmentPortError, ModelPortError

OBS = Observation(
    (CameraImage("head", b"h"), CameraImage("left_wrist", b"l"), CameraImage("right_wrist", b"r")),
    (SceneObject("apple", "object", (1.0, 2.0, 0.9)),),
    {"base_pose": [0, 0, 0], "held_right": None, "held_left": None},
    ({"atom": "inside(apple, fruit_basket)", "holds": False},),
)
CONTINUE = {"kind": "continue"}
FINISH = {"kind": "finish"}


def plan(*subgoal_ids):
    return {
        "schema_version": 2,
        "kind": "task_plan",
        "subgoals": [{"id": sid, "goal": f"do {sid}"} for sid in subgoal_ids],
        "subgraphs": [
            {
                "schema_version": 2,
                "kind": "skill_subgraph",
                "subgoal_id": sid,
                "nodes": [
                    {
                        "id": "n1",
                        "skill": "pick",
                        "args": {"object": {"ref": "apple"}},
                        "depends_on": [],
                    }
                ],
            }
            for sid in subgoal_ids
        ],
    }


def ok(calls):
    return [ContractResult(c.contract, c.args, True, None, None, (), (), {}, None) for c in calls]


def fail(code="PRECONDITION_FAILED"):
    def reply(calls):
        condition = {"atom": "hand_empty(hand=right)", "holds": False}
        return [
            ContractResult(
                calls[0].contract, calls[0].args, False, code, "no", (condition,), (), {}, None
            )
        ]

    return reply


class Environment:
    """Test double for EnvironmentPort: scripted do_contract replies, one exp."""

    def __init__(self, *replies, success=True):
        self.replies = list(replies)
        self.batches = []
        self.checks = []
        self.success = success

    def initial_task(self, task_id):
        return StartedTask("exp-1", TaskInfo(task_id, task_id, "Put the apple away."), OBS)

    def do_contract(self, exp_id, calls):
        self.batches.append([c.contract for c in calls])
        reply = self.replies.pop(0) if self.replies else ok
        if isinstance(reply, Exception):
            raise reply
        return ExecutionReply(exp_id, tuple(reply(calls)), OBS)

    def check_task(self, exp_id):
        self.checks.append(exp_id)
        atom = {"atom": "inside(apple, fruit_basket)", "holds": self.success}
        return GoalCheck(exp_id, self.success, (atom,))


class Session:
    """Test double for PlanningSessionPort: scripted replies."""

    session_id = "session-1"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.turns = []

    def ask(self, text, images=()):
        self.turns.append((text, images))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


class EpisodeRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library = ZenoBenchLibrary()
        cls.catalog = library.load()
        cls.meanings = library.predicate_meanings()

    def run_episode(self, environment, session, limits=EpisodeLimits(), clock=None):
        recorder = MemoryRecorder()
        runner = EpisodeRunner(
            environment,
            session,
            self.catalog,
            recorder,
            predicate_meanings=self.meanings,
            limits=limits,
            **({} if clock is None else {"clock": clock}),
        )
        return runner.run("collect_fruits"), recorder

    def test_plan_continue_finish(self):
        environment = Environment()
        session = Session(plan("a", "b"), CONTINUE, FINISH)

        result, recorder = self.run_episode(environment, session)

        self.assertEqual(("success", "model_finished"), (result.status, result.reason))
        self.assertEqual([["pick"], ["pick"]], environment.batches)
        self.assertEqual(["exp-1"], environment.checks)
        self.assertEqual(3, len(session.turns))
        self.assertTrue(all(len(images) == 3 for _, images in session.turns))
        self.assertIn('"subgoal_result"', session.turns[1][0])
        self.assertIn(ALL_DONE, session.turns[2][0])
        for text, _ in session.turns:
            self.assertNotIn("inside(apple, fruit_basket)", text)
        self.assertEqual("session-1", result.session_id)
        self.assertEqual((2, 0), (result.subgoal_runs, result.replans))
        self.assertIn("check", recorder.kinds())
        logged = dict(recorder.events)["subgoal_run"]["observation"]["task_status"]
        self.assertEqual("inside(apple, fruit_basket)", logged[0]["atom"])

    def test_continue_after_failure_is_rejected_then_replan_runs(self):
        environment = Environment(fail())
        session = Session(plan("a"), CONTINUE, plan("a"), FINISH)

        result, _ = self.run_episode(environment, session)

        self.assertEqual(("success", "model_finished"), (result.status, result.reason))
        self.assertEqual(1, result.replans)
        self.assertEqual(2, len(environment.batches))
        self.assertIn("The given gripper holds nothing.", session.turns[1][0])
        self.assertIn("continue_not_allowed", session.turns[2][0])

    def test_replan_limit(self):
        environment = Environment(fail(), fail())
        session = Session(plan("a"), plan("a"), plan("a"))

        result, _ = self.run_episode(environment, session, EpisodeLimits(max_replans=1))

        self.assertEqual("replan_limit", result.reason)
        self.assertEqual(["exp-1"], environment.checks)

    def test_model_gives_up_after_invalid_replies(self):
        environment = Environment(success=False)
        session = Session("{bad", "{bad", "{bad")

        result, _ = self.run_episode(environment, session)

        self.assertEqual(("failure", "model_gave_up"), (result.status, result.reason))
        self.assertEqual([], environment.batches)
        self.assertEqual(3, len(session.turns))
        self.assertIn("json_syntax", session.turns[1][0])

    def test_model_error_without_output_ends_at_once(self):
        environment = Environment(success=False)
        session = Session(ModelPortError("Harness turn timed out after 300 seconds"))

        result, recorder = self.run_episode(environment, session)

        self.assertEqual("model_error", result.reason)
        self.assertEqual(1, len(session.turns))
        self.assertIn("model_error", recorder.kinds())
        self.assertEqual(["exp-1"], environment.checks)

    def test_sdk_failure_is_a_model_error(self):
        environment = Environment(success=False)
        session = Session(RuntimeError("connection refused"))

        result, _ = self.run_episode(environment, session)

        self.assertEqual("model_error", result.reason)
        self.assertEqual(1, len(session.turns))
        self.assertEqual(["exp-1"], environment.checks)

    def test_partial_outputs_until_attempts_run_out_give_up(self):
        environment = Environment(success=False)
        partial = ModelPortError("max tokens", partial_output='{"kind"')
        session = Session(partial, partial, partial)

        result, _ = self.run_episode(environment, session)

        self.assertEqual("model_gave_up", result.reason)
        self.assertEqual(3, len(session.turns))
        self.assertIn("model_output_incomplete", session.turns[1][0])

    def test_time_budget_stops_before_running(self):
        clock = itertools.chain([0.0], itertools.repeat(1620.0)).__next__
        environment = Environment()
        session = Session(plan("a"))

        result, _ = self.run_episode(environment, session, clock=clock)

        self.assertEqual("time_budget", result.reason)
        self.assertEqual([], environment.batches)
        self.assertEqual(["exp-1"], environment.checks)

    def test_call_limit_ends_without_asking_the_model(self):
        environment = Environment(fail("LIMIT_EXCEEDED"))
        session = Session(plan("a"))

        result, _ = self.run_episode(environment, session)

        self.assertEqual("limit_exceeded", result.reason)
        self.assertEqual(1, len(session.turns))

    def test_released_exp_propagates_without_check(self):
        gone = EnvironmentPortError("released", error_code="EXP_RELEASED", http_status=410)
        environment = Environment(gone)

        with self.assertRaises(EnvironmentPortError):
            self.run_episode(environment, Session(plan("a")))
        self.assertEqual([], environment.checks)

    def test_other_environment_error_releases_the_simulator(self):
        broken = EnvironmentPortError("bad reply", error_code="BAD_RESPONSE")
        environment = Environment(broken)

        with self.assertRaises(EnvironmentPortError):
            self.run_episode(environment, Session(plan("a")))
        self.assertEqual(["exp-1"], environment.checks)


if __name__ == "__main__":
    unittest.main()
