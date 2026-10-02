"""The optional SDK backend lets Harness own all conversation history."""

import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from graph_manager.adapters.deepseek_harness_sdk import DeepSeekHarnessSession
from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.application.harness_planning import HarnessPlanningService
from graph_manager.application.planning_loop import PlanningFailure
from graph_manager.domain.models import PlanningRequest
from graph_manager.ports import ModelPortError

ROOT = Path(__file__).resolve().parents[1]


def valid_plan(skill_id="skill_004"):
    return {
        "schema_version": 1,
        "kind": "task_plan",
        "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
        "subgraphs": [
            {
                "subgoal_id": "sg_1",
                "nodes": [
                    {
                        "id": "n1",
                        "skill_id": skill_id,
                        "args": {"object": {"ref": "apple"}},
                        "depends_on": [],
                    }
                ],
            }
        ],
    }


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
            model="local-vlm",
            provider="lab-vlm",
            profile="sdk",
            patches=(ROOT / "planner.patch.yml",),
            session_id="plan-1",
        )

    def test_image_and_feedback_use_one_persistent_sdk_session(self):
        FakeHarness.outputs = ["first response", "second response"]
        with self.session() as session:
            first = session.ask("Hold apple", b"image-bytes", "image/png")
            second = session.ask('{"kind":"validation_feedback"}')
        harness = FakeHarness.instances[0]
        self.assertEqual(("first response", "second response"), (first, second))
        self.assertEqual(["plan-1"], harness.session_ids)
        self.assertEqual("lab-vlm", harness.kwargs["provider"])
        self.assertEqual("sdk", harness.kwargs["profile"])
        self.assertEqual(2, len(harness.kwargs["patches"]))
        planner_patch, route_patch = harness.kwargs["patches"]
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

    def test_planner_sends_validation_error_without_replaying_history(self):
        FakeHarness.outputs = [
            json.dumps(valid_plan("made_up_skill")),
            json.dumps(valid_plan()),
        ]
        repository = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")
        with self.session() as session:
            result = HarnessPlanningService(repository, session).run(PlanningRequest("Hold apple"))
        inputs = FakeHarness.instances[0].session.inputs
        self.assertEqual(2, len(inputs))
        self.assertIn("Hold apple", inputs[0])
        self.assertIn("skill_009", inputs[0])
        feedback = json.loads(inputs[1])
        self.assertEqual("validation_feedback", feedback["kind"])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", feedback["errors"][0]["path"])
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
                model="local-vlm",
                profile="sdk-minimal",
            )

    def test_turn_deadline_must_be_finite(self):
        for deadline in (float("inf"), float("nan")):
            with self.subTest(deadline=deadline), self.assertRaisesRegex(ValueError, "finite"):
                DeepSeekHarnessSession(
                    dsh_home=ROOT / "run" / "dsh-home",
                    cwd=ROOT,
                    model="local-vlm",
                    turn_timeout_seconds=deadline,
                )

    def test_turn_deadline_cannot_exceed_one_day(self):
        with self.assertRaisesRegex(ValueError, "one day"):
            DeepSeekHarnessSession(
                dsh_home=ROOT / "run" / "dsh-home",
                cwd=ROOT,
                model="local-vlm",
                turn_timeout_seconds=1e308,
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
        repository = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")
        with self.session() as session:
            result = HarnessPlanningService(repository, session).run(PlanningRequest("Hold apple"))
        feedback = json.loads(FakeHarness.instances[0].session.inputs[1])
        self.assertEqual("model_output_incomplete", feedback["errors"][0]["code"])
        self.assertEqual(2, len(result.attempts))

    def test_service_rejects_after_bounded_attempts(self):
        FakeHarness.outputs = [json.dumps(valid_plan("bad-1")), json.dumps(valid_plan("bad-2"))]
        repository = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")
        with self.session() as session:
            with self.assertRaises(PlanningFailure) as caught:
                HarnessPlanningService(repository, session, max_attempts=2).run(
                    PlanningRequest("Hold apple")
                )
        self.assertEqual(2, len(caught.exception.attempts))
        self.assertEqual("unknown_skill", caught.exception.issues[0].code)


if __name__ == "__main__":
    unittest.main()
