"""The SDK adapter lets Harness own all conversation history."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from graph_manager.adapters.deepseek_harness_sdk import DeepSeekHarnessSession, submitted_answer
from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.application.errors import PlanningFailure
from graph_manager.application.planning_service import PlanningService
from graph_manager.domain.models import ImageInput, PlanningRequest
from graph_manager.ports import ModelPortError

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "graph_manager" / "vendor" / "zenobench" / "skills"


def valid_plan(skill="pick"):
    return {
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
                        "skill": skill,
                        "args": {"object": {"ref": "apple"}},
                        "depends_on": [],
                    }
                ],
            }
        ],
    }


def submitted(name, arguments, accepted=True, call_id="call-1"):
    """Harness events for one submit tool call and its result."""
    return [
        {
            "type": "tool/call",
            "data": {"callId": call_id, "name": name, "arguments": json.dumps(arguments)},
        },
        {
            "type": "tool/result",
            "data": {
                "message": {
                    "content": [
                        {
                            "type": "tool-result",
                            "toolCallId": call_id,
                            "content": [{"type": "text", "text": "result"}],
                            "isError": not accepted,
                        }
                    ]
                }
            },
        },
    ]


def turn(events, final_response="Done.", finish_reason="completed"):
    return SimpleNamespace(
        final_response=final_response, finish_reason=finish_reason, events=events
    )


PLAN_TOOL = "mcp__graph__submit_plan"
DECISION_TOOL = "mcp__graph__submit_decision"


class FakeSession:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.inputs = []

    def run(self, value):
        self.inputs.append(value)
        output = next(self.outputs)
        if isinstance(output, str):
            return SimpleNamespace(final_response=output, finish_reason="completed")
        return output


class FakeHarness:
    outputs = []
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session = FakeSession(self.outputs)
        self.session_ids = []
        self.closed = False
        self.instances.append(self)

    def start_session(self, session_id):
        self.session_ids.append(session_id)
        return self.session

    def close(self):
        self.closed = True


class DeepSeekHarnessSessionTest(unittest.TestCase):
    def setUp(self):
        FakeHarness.instances = []
        self.patcher = patch(
            "graph_manager.adapters.deepseek_harness_sdk._load_harness_class",
            return_value=FakeHarness,
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def session(self):
        return DeepSeekHarnessSession(
            dsh_home=ROOT / "run" / "dsh-home",
            cwd=ROOT,
            skills_dir=SKILLS,
            model="local-vlm",
            provider="lab-vlm",
            profile="sdk",
            patches=(ROOT / "planner.patch.yml",),
            session_id="plan-1",
        )

    def test_image_and_feedback_use_one_persistent_sdk_session(self):
        FakeHarness.outputs = ["first response", "second response"]
        with self.session() as session:
            first = session.ask("Hold apple", (ImageInput(b"image-bytes", "image/png"),))
            second = session.ask('{"kind":"validation_feedback"}')
        harness = FakeHarness.instances[0]
        self.assertEqual(("first response", "second response"), (first, second))
        self.assertEqual(["plan-1"], harness.session_ids)
        self.assertEqual("lab-vlm", harness.kwargs["provider"])
        self.assertEqual("sdk", harness.kwargs["profile"])
        self.assertEqual(4, len(harness.kwargs["patches"]))
        planner_patch, skills_patch, submit_patch, route_patch = harness.kwargs["patches"]
        self.assertEqual(
            str(ROOT / "run" / "dsh-home" / "graph-manager-submit.patch.yml"), submit_patch
        )
        self.assertEqual(
            str(ROOT / "run" / "dsh-home" / "graph-manager-skills.patch.yml"), skills_patch
        )
        self.assertEqual(str(ROOT / "planner.patch.yml"), route_patch)
        self.assertTrue(Path(planner_patch).is_file())
        self.assertIn("graph_manager", Path(planner_patch).parts)
        blocks = harness.session.inputs[0]
        self.assertEqual([{"type": "text", "text": "Hold apple"}], blocks[:1])
        self.assertEqual(
            {"type": "image", "mimeType": "image/png", "data": "aW1hZ2UtYnl0ZXM="},
            blocks[1],
        )
        self.assertEqual('{"kind":"validation_feedback"}', harness.session.inputs[1])
        self.assertTrue(harness.closed)

    def test_several_images_follow_the_text_in_order(self):
        FakeHarness.outputs = ["ok"]
        with self.session() as session:
            session.ask("Look", (ImageInput(b"head"), ImageInput(b"left", "image/jpeg")))
        blocks = FakeHarness.instances[0].session.inputs[0]
        self.assertEqual(
            [
                {"type": "text", "text": "Look"},
                {"type": "image", "data": "aGVhZA==", "mimeType": "image/png"},
                {"type": "image", "data": "bGVmdA==", "mimeType": "image/jpeg"},
            ],
            blocks,
        )

    def test_planner_sends_validation_error_without_replaying_history(self):
        FakeHarness.outputs = [
            json.dumps(valid_plan("made_up_skill")),
            json.dumps(valid_plan()),
        ]
        repository = ZenoBenchLibrary()
        with self.session() as session:
            result = PlanningService(repository, session).run(PlanningRequest("Hold apple"))
        inputs = FakeHarness.instances[0].session.inputs
        self.assertEqual(2, len(inputs))
        self.assertIn("Hold apple", inputs[0])
        feedback = json.loads(inputs[1])
        self.assertEqual("validation_feedback", feedback["kind"])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill", feedback["errors"][0]["path"])
        self.assertEqual(2, len(result.attempts))

    def test_truncated_sdk_turn_preserves_partial_output_for_repair(self):
        FakeHarness.outputs = [
            SimpleNamespace(final_response='{"partial":', finish_reason="max-tokens")
        ]
        with self.session() as session:
            with self.assertRaises(ModelPortError) as caught:
                session.ask("Go")
        self.assertEqual('{"partial":', caught.exception.partial_output)

    def test_only_verified_sdk_profile_is_accepted(self):
        with self.assertRaisesRegex(ValueError, "sdk"):
            DeepSeekHarnessSession(
                dsh_home=ROOT / "run" / "dsh-home",
                cwd=ROOT,
                skills_dir=SKILLS,
                model="local-vlm",
                profile="sdk-minimal",
            )

    def test_turn_deadline_must_be_finite(self):
        for deadline in (float("inf"), float("nan")):
            with self.subTest(deadline=deadline), self.assertRaisesRegex(ValueError, "finite"):
                DeepSeekHarnessSession(
                    dsh_home=ROOT / "run" / "dsh-home",
                    cwd=ROOT,
                    skills_dir=SKILLS,
                    model="local-vlm",
                    turn_timeout_seconds=deadline,
                )

    def test_turn_deadline_cannot_exceed_one_day(self):
        with self.assertRaisesRegex(ValueError, "one day"):
            DeepSeekHarnessSession(
                dsh_home=ROOT / "run" / "dsh-home",
                cwd=ROOT,
                skills_dir=SKILLS,
                model="local-vlm",
                turn_timeout_seconds=1e308,
            )

    def test_skills_patch_exposes_only_the_zenobench_skills(self):
        FakeHarness.outputs = ["ok"]
        with self.session() as session:
            session.ask("Go")
        written = json.loads(Path(FakeHarness.instances[0].kwargs["patches"][1]).read_text())
        self.assertEqual(
            [
                {
                    "id": "skill-filesystem",
                    "config": {
                        "includeDefaultRoots": False,
                        "watch": False,
                        "customSkillDirs": [str(SKILLS.resolve())],
                    },
                }
            ],
            written,
        )
        planner_profile = (
            ROOT / "graph_manager" / "harness_profile" / "cordis.patch.yml"
        ).read_text()
        for component in ("id: skill\n", "id: skill-filesystem\n", "id: tool-skill\n"):
            self.assertNotIn(component, planner_profile)

    def test_skills_patch_write_leaves_no_temporary_files(self):
        FakeHarness.outputs = ["ok"]
        with tempfile.TemporaryDirectory() as directory:
            dsh_home = Path(directory)
            with DeepSeekHarnessSession(
                dsh_home=dsh_home, cwd=ROOT, skills_dir=SKILLS, model="local-vlm"
            ) as session:
                session.ask("Go")
            self.assertEqual([], list(dsh_home.glob("*.tmp")) + list(dsh_home.glob(".*.tmp")))
            self.assertEqual(
                ["graph-manager-skills.patch.yml", "graph-manager-submit.patch.yml"],
                sorted(p.name for p in dsh_home.iterdir()),
            )

    def test_submit_patch_starts_the_mcp_server_with_this_python(self):
        FakeHarness.outputs = ["ok"]
        with self.session() as session:
            session.ask("Go")
        written = json.loads(Path(FakeHarness.instances[0].kwargs["patches"][2]).read_text())
        self.assertEqual(
            [
                {
                    "insert": [
                        {
                            "id": "mcp-graph-submit",
                            "name": "@deepseek-ai/dsh-mcp-client",
                            "config": {
                                "serverName": "graph",
                                "transport": "stdio",
                                "command": sys.executable,
                                "args": [
                                    "-m",
                                    "graph_manager.adapters.submit_tools",
                                    "--zenobench-root",
                                    str(SKILLS.resolve().parent),
                                ],
                                "failOnStartupError": True,
                            },
                        }
                    ]
                }
            ],
            written,
        )

    def test_last_accepted_submission_is_the_answer(self):
        events = submitted(PLAN_TOOL, {"bad": 1}, accepted=False, call_id="c1") + submitted(
            PLAN_TOOL, valid_plan(), call_id="c2"
        )
        FakeHarness.outputs = [turn(events)]
        with self.session() as session:
            answer = session.ask("Go")
        self.assertEqual(valid_plan(), json.loads(answer))

    def test_rejected_submission_is_returned_for_validation(self):
        FakeHarness.outputs = [turn(submitted(PLAN_TOOL, valid_plan("grab"), accepted=False))]
        with self.session() as session:
            answer = session.ask("Go")
        self.assertEqual(valid_plan("grab"), json.loads(answer))

    def test_decision_submission_is_the_answer(self):
        FakeHarness.outputs = [turn(submitted(DECISION_TOOL, {"kind": "finish"}))]
        with self.session() as session:
            self.assertEqual({"kind": "finish"}, json.loads(session.ask("Next?")))

    def test_without_a_submission_the_final_text_is_returned(self):
        skill_call = [
            {
                "type": "tool/call",
                "data": {"callId": "s", "name": "skill", "arguments": '{"name": "pick-object"}'},
            }
        ]
        FakeHarness.outputs = [turn(skill_call, final_response="plain text")]
        with self.session() as session:
            self.assertEqual("plain text", session.ask("Go"))

    def test_accepted_submission_wins_over_an_unfinished_turn(self):
        FakeHarness.outputs = [
            turn(submitted(PLAN_TOOL, valid_plan()), final_response="", finish_reason="max-tokens")
        ]
        with self.session() as session:
            self.assertEqual(valid_plan(), json.loads(session.ask("Go")))

    def test_submitted_answer_ignores_other_tools(self):
        events = [
            {"type": "tool/call", "data": {"callId": "x", "name": "skill", "arguments": "{}"}}
        ]
        self.assertIsNone(submitted_answer(events))

    def test_planner_uses_the_submitted_plan(self):
        FakeHarness.outputs = [turn(submitted(PLAN_TOOL, valid_plan()))]
        with self.session() as session:
            result = PlanningService(ZenoBenchLibrary(), session).run(PlanningRequest("Hold apple"))
        self.assertEqual(valid_plan(), result.task_plan)

    def test_skills_dir_must_exist(self):
        with self.assertRaisesRegex(ValueError, "skills directory"):
            DeepSeekHarnessSession(
                dsh_home=ROOT / "run" / "dsh-home",
                cwd=ROOT,
                model="local-vlm",
                skills_dir=ROOT / "no-such-skills",
            )

    def test_stalled_turn_closes_harness_after_deadline(self):
        released = threading.Event()

        class BlockingHarness(FakeHarness):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.session = self

            def run(self, _value):
                released.wait(1)
                return SimpleNamespace(final_response="late", finish_reason="completed")

            def close(self):
                released.set()
                super().close()

        with patch(
            "graph_manager.adapters.deepseek_harness_sdk._load_harness_class",
            return_value=BlockingHarness,
        ):
            with DeepSeekHarnessSession(
                dsh_home=ROOT / "run" / "dsh-home",
                cwd=ROOT,
                skills_dir=SKILLS,
                model="local-vlm",
                turn_timeout_seconds=0.05,
            ) as session:
                with self.assertRaisesRegex(ModelPortError, "timed out"):
                    session.ask("Reply once")
        self.assertTrue(BlockingHarness.instances[-1].closed)

    def test_late_timer_callback_does_not_close_completed_session(self):
        timers = []

        class LateTimer:
            def __init__(self, _seconds, callback):
                self.callback = callback
                timers.append(self)

            def start(self):
                pass

            def cancel(self):
                pass

        FakeHarness.outputs = ["first", "second"]
        with patch("graph_manager.adapters.deepseek_harness_sdk.threading.Timer", LateTimer):
            with self.session() as session:
                self.assertEqual("first", session.ask("first prompt"))
                timers[0].callback()
                self.assertFalse(FakeHarness.instances[0].closed)
                self.assertEqual("second", session.ask("second prompt"))

    def test_service_repairs_incomplete_turn_in_same_session(self):
        FakeHarness.outputs = [
            SimpleNamespace(final_response='{"partial":', finish_reason="max-tokens"),
            json.dumps(valid_plan()),
        ]
        repository = ZenoBenchLibrary()
        with self.session() as session:
            result = PlanningService(repository, session).run(PlanningRequest("Hold apple"))
        feedback = json.loads(FakeHarness.instances[0].session.inputs[1])
        self.assertEqual("model_output_incomplete", feedback["errors"][0]["code"])
        self.assertEqual(2, len(result.attempts))

    def test_service_rejects_after_bounded_attempts(self):
        FakeHarness.outputs = [json.dumps(valid_plan("bad-1")), json.dumps(valid_plan("bad-2"))]
        repository = ZenoBenchLibrary()
        with self.session() as session:
            with self.assertRaises(PlanningFailure) as caught:
                PlanningService(repository, session, max_attempts=2).run(
                    PlanningRequest("Hold apple")
                )
        self.assertEqual(2, len(caught.exception.attempts))
        self.assertEqual("unknown_skill", caught.exception.issues[0].code)


if __name__ == "__main__":
    unittest.main()
