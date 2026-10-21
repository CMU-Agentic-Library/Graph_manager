# Harness-Only Planning Architecture Implementation Plan

> **Historical:** this document records an earlier design and is superseded. See README.md for the current behavior (schema 2, vendored ZenoBench skills, `graph-manager-run`).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DeepSeek Harness the sole model runtime and keep one clear Graph Manager planning path: build model input, validate the returned plan, and orchestrate corrective turns in one Harness session.

**Architecture:** A dedicated input builder produces the initial model turn and validation feedback. One application service loads the public Skill Library, asks a session for candidate plans, and calls the existing pure domain validator. The DeepSeek adapter owns SDK-specific serialization and session lifetime; the CLI only reads files and wires dependencies. Robot Skill execution is a separate later subsystem.

**Tech Stack:** Python 3.12+, standard-library `unittest`, DeepSeek Harness Python SDK `0.1.5rc1`, `uv`, Ruff, JSON Contracts.

---

## Scope and source of truth

The agreed behavior is **one complete `task_plan` response containing all Subgoals and one Skill Subgraph per Subgoal**. Preserve the current JSON schema, public Library, optional image/observation/entity catalog/state inputs, bounded validation feedback in the same Harness session, `PlanningResult` statuses, and precise error paths. The current `graph_manager/domain/task_plan_validation.py` is the plan validator; do not rewrite its semantics during this refactor.

This plan does not build a ZenoBench graph runner, simulator observation adapter, independent visual Verifier, per-Subgoal execution loop, or a new model-serving process. A local Qwen/VLM still needs an OpenAI-compatible serving endpoint; Harness connects to that endpoint through `examples/harness-local-vlm.patch.yml`.

Before execution, use the `using-git-worktrees` skill to create an isolated worktree. From the repository root, record the baseline:

~~~bash
uv sync --locked --extra dev --extra harness
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
~~~

Expected on the current main branch: `Ran 73 tests`, `OK`, and both Ruff checks pass.

## File map

| Path | Responsibility after the refactor |
|---|---|
| `graph_manager/application/input_builder.py` | Build one initial model turn from request + public Library; build feedback turns without replaying context. |
| `graph_manager/application/planning_service.py` | Sole planning orchestration and bounded acceptance policy. |
| `graph_manager/prompts/task_plan.py` | Own the model-visible plan instructions and text rendering; existing wording is reused. |
| `graph_manager/domain/task_plan_validation.py` | Pure JSON, Contract, argument, reference, condition, and DAG checks; unchanged. |
| `graph_manager/adapters/deepseek_harness_sdk.py` | Translate a turn into SDK text/image blocks and return `final_response`; unchanged. |
| `graph_manager/adapters/skill_library_json.py` | Load the public JSON catalog; unchanged. |
| `graph_manager/cli.py` | Sole command-line controller; construct the Harness session and PlanningService. |
| `graph_manager/plan_inputs.py` | Read Goal, image, observation, entity IDs/types, and observed facts from CLI files; unchanged. |
| `graph_manager/ports.py` | Retain the session and Library protocols; remove the direct HTTP model protocol. |
| `pyproject.toml` and `uv.lock` | Make the pinned Harness SDK the runtime dependency; expose one `graph-manager-plan` command. |
| `README.md` | Explain the single planning path and local model setup. |

Delete the obsolete direct HTTP adapter, Python-owned conversation, duplicate application loops and CLI, and their backend-specific tests only after the sole path has equivalent tests. Keep the existing SDK adapter tests.

### Task 1: Create the model input builder

**Files:**
- Create: `graph_manager/application/input_builder.py`
- Create: `tests/test_input_builder.py`
- Read: `graph_manager/prompts/task_plan.py`

- [x] **Step 1: Write the failing input-builder test**

Create `tests/test_input_builder.py` with:

~~~python
"""Model-visible turns are built before they reach the Harness adapter."""

import json
import unittest

from graph_manager.application.input_builder import PlanningInputBuilder
from graph_manager.domain.models import (
    EntityCatalog,
    ObservedState,
    PlanningRequest,
    ValidationIssue,
)


class PlanningInputBuilderTest(unittest.TestCase):
    def test_initial_turn_contains_public_context_and_original_image(self):
        catalog = EntityCatalog.from_json(
            {"entities": [{"id": "apple", "types": ["MovableObject"]}]}
        )
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": True}]}
        )
        request = PlanningRequest(
            "Hold apple",
            image=b"image-bytes",
            image_mime="image/png",
            observation="Apple visible",
            entity_catalog=catalog,
            state=state,
        )
        library = {"version": 1, "skills": [{"id": "skill_004"}], "types": {}}

        turn = PlanningInputBuilder().initial(request, library)

        self.assertIn("Return exactly one JSON object", turn.text)
        self.assertIn("Hold apple", turn.text)
        self.assertIn("Apple visible", turn.text)
        self.assertIn('"id": "skill_004"', turn.text)
        self.assertIn('"id": "apple"', turn.text)
        self.assertIn("gripper_empty", turn.text)
        self.assertEqual(b"image-bytes", turn.image)
        self.assertEqual("image/png", turn.image_mime)

    def test_absent_optional_sources_are_not_invented(self):
        library = {"version": 1, "skills": [], "types": {}}

        turn = PlanningInputBuilder().initial(PlanningRequest("Hold apple"), library)

        self.assertNotIn("GT entity catalog (use exact IDs", turn.text)
        self.assertNotIn("Verified current state facts", turn.text)
        self.assertIsNone(turn.image)

    def test_feedback_turn_contains_only_errors_and_no_image(self):
        issue = ValidationIssue(
            "$.subgraphs[0].nodes[0].skill_id", "unknown_skill", "unknown Skill ID"
        )

        turn = PlanningInputBuilder().feedback((issue,))

        self.assertIsNone(turn.image)
        self.assertEqual("image/jpeg", turn.image_mime)
        body = json.loads(turn.text)
        self.assertEqual("validation_feedback", body["kind"])
        self.assertEqual("unknown_skill", body["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", body["errors"][0]["path"])


if __name__ == "__main__":
    unittest.main()
~~~

- [x] **Step 2: Run the focused test to see the missing-module failure**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_input_builder.py' -v
~~~

Expected: FAIL with `ModuleNotFoundError: No module named 'graph_manager.application.input_builder'`.

- [x] **Step 3: Add the complete input builder**

Create `graph_manager/application/input_builder.py`:

~~~python
"""Build model-visible planning turns independently of the model transport."""

from dataclasses import dataclass

from ..domain.models import PlanningRequest, ValidationIssue
from ..prompts.task_plan import SYSTEM_INSTRUCTION, initial_context, validation_feedback


@dataclass(frozen=True)
class ModelTurn:
    text: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"


class PlanningInputBuilder:
    def initial(self, request: PlanningRequest, library: dict) -> ModelTurn:
        return ModelTurn(
            text=SYSTEM_INSTRUCTION + "\n\n" + initial_context(request, library),
            image=request.image,
            image_mime=request.image_mime,
        )

    def feedback(self, issues: tuple[ValidationIssue, ...]) -> ModelTurn:
        return ModelTurn(text=validation_feedback(issues))
~~~

- [x] **Step 4: Run the focused test and lint**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_input_builder.py' -v
.venv/bin/ruff check graph_manager/application/input_builder.py tests/test_input_builder.py
~~~

Expected: all three tests pass and Ruff reports `All checks passed!`.

- [x] **Step 5: Commit the input boundary**

~~~bash
git add graph_manager/application/input_builder.py tests/test_input_builder.py
git commit -m "refactor: isolate planning model input builder"
~~~

### Task 2: Build one planning service around the existing validator

**Files:**
- Create: `graph_manager/application/planning_service.py`
- Create: `tests/test_planning_service.py`
- Read: `graph_manager/domain/task_plan_validation.py` and `graph_manager/application/errors.py`

- [x] **Step 1: Write focused tests for one-session orchestration**

Create `tests/test_planning_service.py`:

~~~python
"""The planning service owns task policy, not SDK conversation storage."""

import json
import unittest
from pathlib import Path

from graph_manager.adapters.skill_library_json import JsonSkillLibraryRepository
from graph_manager.application.errors import PlanningFailure
from graph_manager.application.planning_service import PlanningService
from graph_manager.domain.models import ObservedState, PlanningRequest
from graph_manager.ports import ModelPortError

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json")


def proposal(skill_id="skill_004"):
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


class ScriptedSession:
    session_id = "test-session"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.turns = []

    def ask(self, text, image=None, image_mime="image/jpeg"):
        self.turns.append((text, image, image_mime))
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return json.dumps(output) if isinstance(output, dict) else output


class PlanningServiceTest(unittest.TestCase):
    def test_valid_plan_uses_one_turn_and_preserves_image(self):
        session = ScriptedSession([proposal()])

        result = PlanningService(REPOSITORY, session).run(
            PlanningRequest("Hold apple", image=b"pixels", image_mime="image/png")
        )

        self.assertEqual(proposal(), result.task_plan)
        self.assertEqual(1, len(result.attempts))
        self.assertEqual("unresolved_references", result.to_json()["status"])
        self.assertEqual(b"pixels", session.turns[0][1])
        self.assertEqual("image/png", session.turns[0][2])

    def test_invalid_skill_sends_only_feedback_as_second_turn(self):
        session = ScriptedSession([proposal("invented_skill"), proposal()])

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual(2, len(result.attempts))
        self.assertEqual(2, len(session.turns))
        self.assertIn("Complete public Skill Library JSON", session.turns[0][0])
        self.assertNotIn("Complete public Skill Library JSON", session.turns[1][0])
        self.assertIsNone(session.turns[1][1])
        feedback = json.loads(session.turns[1][0])
        self.assertEqual("unknown_skill", feedback["errors"][0]["code"])
        self.assertEqual("$.subgraphs[0].nodes[0].skill_id", feedback["errors"][0]["path"])

    def test_invalid_json_generates_feedback_in_same_session(self):
        session = ScriptedSession(["{not-json", proposal()])

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual(2, len(result.attempts))
        self.assertEqual("json_syntax", json.loads(session.turns[1][0])["errors"][0]["code"])

    def test_incomplete_model_turn_is_recorded_and_repaired(self):
        session = ScriptedSession(
            [ModelPortError("max-tokens", partial_output='{"partial":'), proposal()]
        )

        result = PlanningService(REPOSITORY, session).run(PlanningRequest("Hold apple"))

        self.assertEqual('{"partial":', result.attempts[0].raw_text)
        self.assertEqual("model_output_incomplete", result.attempts[0].issues[0].code)
        self.assertEqual(
            "model_output_incomplete",
            json.loads(session.turns[1][0])["errors"][0]["code"],
        )

    def test_known_false_initial_fact_rejects_after_limit(self):
        state = ObservedState.from_json(
            {"facts": [{"predicate": "gripper_empty", "args": {}, "value": False}]}
        )
        session = ScriptedSession([proposal()])

        with self.assertRaises(PlanningFailure) as caught:
            PlanningService(REPOSITORY, session, max_attempts=1).run(
                PlanningRequest("Hold apple", state=state)
            )

        self.assertEqual("precondition_failed", caught.exception.issues[0].code)
        self.assertEqual("$.subgraphs[0].nodes[0]", caught.exception.issues[0].path)
        self.assertEqual(1, len(caught.exception.attempts))


if __name__ == "__main__":
    unittest.main()
~~~

- [x] **Step 2: Confirm the new service is absent**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_planning_service.py' -v
~~~

Expected: FAIL with `ModuleNotFoundError: No module named 'graph_manager.application.planning_service'`.

- [x] **Step 3: Add the complete service**

Create `graph_manager/application/planning_service.py`:

~~~python
"""One application-level planning policy for a session-owned model history."""

from ..domain.models import (
    PlanAttempt,
    PlanningRequest,
    PlanningResult,
    ProposalValidationError,
    ValidationIssue,
)
from ..domain.task_plan_validation import validate_task_plan
from ..ports import ModelPortError, PlanningSessionPort, SkillLibraryPort
from .errors import PlanningFailure
from .input_builder import PlanningInputBuilder


class PlanningService:
    def __init__(
        self,
        repository: SkillLibraryPort,
        session: PlanningSessionPort,
        max_attempts: int = 3,
        input_builder: PlanningInputBuilder | None = None,
    ):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        self.repository = repository
        self.session = session
        self.max_attempts = max_attempts
        self.input_builder = input_builder or PlanningInputBuilder()

    def run(self, request: PlanningRequest) -> PlanningResult:
        library = self.repository.load()
        turn = self.input_builder.initial(request, library)
        attempts: list[PlanAttempt] = []

        for attempt_number in range(self.max_attempts):
            try:
                raw_text = self.session.ask(turn.text, turn.image, turn.image_mime)
            except ModelPortError as exc:
                issue = ValidationIssue(
                    "$",
                    "model_output_incomplete" if exc.partial_output is not None else "model_error",
                    str(exc),
                )
                if exc.partial_output is not None:
                    attempts.append(PlanAttempt(exc.partial_output, (issue,)))
                    if attempt_number + 1 < self.max_attempts:
                        turn = self.input_builder.feedback((issue,))
                        continue
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            except Exception as exc:
                issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc

            try:
                plan = validate_task_plan(raw_text, library, request.entity_catalog, request.state)
            except ProposalValidationError as exc:
                attempts.append(PlanAttempt(raw_text, exc.issues))
                if attempt_number + 1 == self.max_attempts:
                    raise PlanningFailure(exc.issues, tuple(attempts)) from exc
                turn = self.input_builder.feedback(exc.issues)
                continue

            attempts.append(PlanAttempt(raw_text, ()))
            return PlanningResult(plan, tuple(attempts), request.entity_catalog is not None)

        raise AssertionError("positive max_attempts guarantees a return or raise")
~~~

- [x] **Step 4: Run focused and full tests**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_planning_service.py' -v
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check graph_manager/application/planning_service.py tests/test_planning_service.py
~~~

Expected: five focused tests pass, the existing suite remains green, and Ruff passes.

- [x] **Step 5: Commit the single service**

~~~bash
git add graph_manager/application/planning_service.py tests/test_planning_service.py
git commit -m "refactor: add one session-based planning service"
~~~

### Task 3: Make the normal CLI use the sole Harness planning path

**Files:**
- Replace: `graph_manager/cli.py`
- Replace: `tests/test_planner_cli.py`
- Read: `graph_manager/harness_cli.py` and `graph_manager/plan_inputs.py`

- [x] **Step 1: Replace the direct HTTP CLI test with a Harness-wiring test**

Replace `tests/test_planner_cli.py` with:

~~~python
"""The public command wires Harness to the single planning service."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_manager.cli import run


class FakeHarnessSession:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_id = kwargs["session_id"] or "generated-session"
        self.dsh_home = Path(kwargs["dsh_home"])
        self.turns = []
        self.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def ask(self, text, image=None, image_mime="image/jpeg"):
        self.turns.append((text, image, image_mime))
        return json.dumps(
            {
                "schema_version": 1,
                "kind": "task_plan",
                "subgoals": [{"id": "sg_1", "goal": "Hold apple"}],
                "subgraphs": [
                    {
                        "subgoal_id": "sg_1",
                        "nodes": [
                            {
                                "id": "n1",
                                "skill_id": "skill_004",
                                "args": {"object": {"ref": "apple"}},
                                "depends_on": [],
                            }
                        ],
                    }
                ],
            }
        )


class PlannerCliTest(unittest.TestCase):
    def setUp(self):
        FakeHarnessSession.created = []

    def test_public_command_saves_grounded_plan_and_session_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "scene.png"
            image.write_bytes(b"pixels")
            catalog = root / "entities.json"
            catalog.write_text(
                json.dumps({"entities": [{"id": "apple", "types": ["MovableObject"]}]})
            )
            patch_file = root / "route.patch.yml"
            patch_file.write_text("[]\n")
            output = root / "plan.json"

            with patch("graph_manager.cli.DeepSeekHarnessSession", FakeHarnessSession):
                exit_code = run(
                    [
                        "--goal",
                        "Hold apple",
                        "--image",
                        str(image),
                        "--entity-catalog",
                        str(catalog),
                        "--dsh-home",
                        str(root / "dsh"),
                        "--provider",
                        "lab-vlm",
                        "--model",
                        "local-vlm",
                        "--patch",
                        str(patch_file),
                        "--output",
                        str(output),
                    ]
                )

            saved = json.loads(output.read_text())
            self.assertEqual(0, exit_code)
            self.assertEqual("statically_validated", saved["status"])
            self.assertEqual("deepseek_harness", saved["runtime"]["backend"])
            self.assertEqual("generated-session", saved["runtime"]["session_id"])
            session = FakeHarnessSession.created[0]
            self.assertEqual("sdk", session.kwargs["profile"])
            self.assertEqual(b"pixels", session.turns[0][1])
            self.assertEqual("image/png", session.turns[0][2])


if __name__ == "__main__":
    unittest.main()
~~~

- [x] **Step 2: Run the test against the old CLI**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_planner_cli.py' -v
~~~

Expected: FAIL because `graph_manager.cli` has no `DeepSeekHarnessSession` attribute.

- [x] **Step 3: Replace the CLI with the complete Harness wiring**

Replace `graph_manager/cli.py` with:

~~~python
"""Command-line controller for one complete-plan Harness session."""

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters.deepseek_harness_sdk import DeepSeekHarnessSession
from .adapters.skill_library_json import JsonSkillLibraryRepository
from .application.errors import PlanningFailure
from .application.planning_service import PlanningService
from .plan_inputs import DEFAULT_LIBRARY, add_request_arguments, read_request


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate a task Skill plan")
    add_request_arguments(parser)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument(
        "--dsh-home", required=True, type=Path, help="local Harness state directory"
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--provider", default="deepseek-official")
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", choices=("sdk",), default="sdk")
    parser.add_argument("--patch", action="append", type=Path, default=[], help="profile patch")
    parser.add_argument("--base-url", help="optional DeepSeek-compatible endpoint override")
    parser.add_argument("--session-id", help="Harness session ID; use a fresh ID per invocation")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--turn-timeout-seconds", type=float, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        request = read_request(args)
        for patch_file in args.patch:
            if not patch_file.is_file():
                raise ValueError(f"Harness patch does not exist: {patch_file}")
        with DeepSeekHarnessSession(
            dsh_home=args.dsh_home,
            cwd=args.workspace,
            model=args.model,
            provider=args.provider,
            profile=args.profile,
            patches=tuple(args.patch),
            base_url=args.base_url,
            api_key=os.getenv("GRAPH_MANAGER_API_KEY"),
            max_tokens=args.max_tokens,
            session_id=args.session_id,
            turn_timeout_seconds=args.turn_timeout_seconds,
        ) as session:
            service = PlanningService(
                JsonSkillLibraryRepository(args.library), session, args.max_attempts
            )
            try:
                result = service.run(request).to_json()
                exit_code = 0
            except PlanningFailure as exc:
                result = exc.to_json()
                exit_code = 1
            result["runtime"] = {
                "backend": "deepseek_harness",
                "profile": args.profile,
                "session_id": session.session_id,
                "dsh_home": str(session.dsh_home),
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"{result['status']}: {args.output}")
        return exit_code
    except (OSError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
~~~

- [x] **Step 4: Run the new CLI test and the regression suite**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_planner_cli.py' -v
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check graph_manager/cli.py tests/test_planner_cli.py
~~~

Expected: the new CLI test passes; existing SDK and domain tests also pass.

- [x] **Step 5: Commit the controller switch**

~~~bash
git add graph_manager/cli.py tests/test_planner_cli.py
git commit -m "refactor: route planner CLI through DeepSeek Harness"
~~~

### Task 4: Retire the duplicate backend and make Harness required

**Files:**
- Modify: `tests/test_deepseek_harness_sdk.py`
- Replace: `graph_manager/ports.py`
- Modify: `graph_manager/domain/models.py`
- Modify: `pyproject.toml`
- Regenerate: `uv.lock`
- Delete: `graph_manager/adapters/openai_compatible.py`, `graph_manager/application/conversation.py`, `graph_manager/application/planning_loop.py`, `graph_manager/application/harness_planning.py`, `graph_manager/harness_cli.py`
- Delete: `tests/test_openai_compatible.py`, `tests/test_planning_context.py`, `tests/test_planning_loop.py`, `tests/test_harness_cli.py`

- [x] **Step 1: Move the existing SDK behavior tests onto the sole service**

Run this exact source edit from the repository root:

~~~bash
.venv/bin/python - <<'PY'
from pathlib import Path

path = Path("tests/test_deepseek_harness_sdk.py")
source = path.read_text(encoding="utf-8")
assert source.count("HarnessPlanningService") == 4
assert source.count("from graph_manager.application.planning_loop import PlanningFailure") == 1
source = source.replace(
    "from graph_manager.application.harness_planning import HarnessPlanningService",
    "from graph_manager.application.planning_service import PlanningService",
)
source = source.replace(
    "from graph_manager.application.planning_loop import PlanningFailure",
    "from graph_manager.application.errors import PlanningFailure",
)
source = source.replace("HarnessPlanningService(", "PlanningService(")
path.write_text(source, encoding="utf-8")
PY
~~~

The four occurrences are one import and three service constructions. The existing tests still assert one SDK session, image transfer, feedback, timeout, partial output, and bounded rejection.

- [x] **Step 2: Check the migrated SDK tests before deleting old code**

~~~bash
.venv/bin/python -m unittest discover -s tests -p 'test_deepseek_harness_sdk.py' -v
~~~

Expected: the SDK adapter and new PlanningService tests pass.

- [x] **Step 3: Delete the obsolete application and direct transport files**

~~~bash
git rm graph_manager/adapters/openai_compatible.py
git rm graph_manager/application/conversation.py
git rm graph_manager/application/planning_loop.py
git rm graph_manager/application/harness_planning.py
git rm graph_manager/harness_cli.py
git rm tests/test_openai_compatible.py
git rm tests/test_planning_context.py
git rm tests/test_planning_loop.py
git rm tests/test_harness_cli.py
~~~

These are the removed duplicate path and its backend-specific tests. `tests/test_input_builder.py`, `tests/test_planning_service.py`, `tests/test_planner_cli.py`, `tests/test_deepseek_harness_sdk.py`, and the existing domain tests provide the replacement coverage.

- [x] **Step 4: Remove the now-unused direct-model types**

Replace `graph_manager/ports.py` with:

~~~python
"""Small interfaces between planning and external adapters."""

from typing import Protocol


class PlanningSessionPort(Protocol):
    """A runtime that retains conversation history between calls."""

    session_id: str

    def ask(self, text: str, image: bytes | None = None, image_mime: str = "image/jpeg") -> str:
        raise NotImplementedError


class SkillLibraryPort(Protocol):
    def load(self) -> dict:
        raise NotImplementedError


class ModelPortError(RuntimeError):
    """A model request failed; a partial output may be repairable."""

    def __init__(self, message: str, partial_output: str | None = None):
        self.partial_output = partial_output
        super().__init__(message)
~~~

Run this exact edit for `graph_manager/domain/models.py`:

~~~bash
.venv/bin/python - <<'PY'
from pathlib import Path

path = Path("graph_manager/domain/models.py")
source = path.read_text(encoding="utf-8")
chat_message = '''@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    text: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"


'''
assert source.count("from typing import Literal\n") == 1
assert source.count(chat_message) == 1
source = source.replace("from typing import Literal\n", "")
source = source.replace(chat_message, "")
path.write_text(source, encoding="utf-8")
PY
~~~

- [x] **Step 5: Keep one installed command and make the SDK a normal dependency**

Run this exact edit for `pyproject.toml`:

~~~bash
.venv/bin/python - <<'PY'
from pathlib import Path

path = Path("pyproject.toml")
source = path.read_text(encoding="utf-8")
old = '''dependencies = []

[project.optional-dependencies]
dev = ["ruff"]
harness = ["deepseek-harness-sdk==0.1.5rc1"]

[project.scripts]
graph-manager-plan = "graph_manager.cli:main"
graph-manager-plan-harness = "graph_manager.harness_cli:main"
'''
new = '''dependencies = ["deepseek-harness-sdk==0.1.5rc1"]

[project.optional-dependencies]
dev = ["ruff"]

[project.scripts]
graph-manager-plan = "graph_manager.cli:main"
'''
assert source.count(old) == 1
path.write_text(source.replace(old, new), encoding="utf-8")
PY
~~~

- [x] **Step 6: Regenerate and sync the lock file**

~~~bash
uv lock
uv sync --locked --extra dev
~~~

Expected: both `uv` commands exit 0, the pinned SDK/runtime are installed into `.venv`, and `uv.lock` records the SDK as a base dependency.

- [x] **Step 7: Verify the single code path and all tests**

~~~bash
rg -n 'PlanningLoop|HarnessPlanningService|OpenAICompatibleModel|Conversation|ChatMessage|graph-manager-plan-harness|harness_cli|application\.planning_loop|application\.harness_planning' graph_manager tests pyproject.toml
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/graph-manager-plan --help
~~~

Expected: `rg` returns no matches (exit 1); tests end with `OK`; both Ruff checks pass; the sole command shows `--dsh-home`, `--model`, `--image`, and `--output`. If the formatter reports only formatting differences, run `.venv/bin/ruff format graph_manager tests` and repeat the checks before committing.

- [x] **Step 8: Commit the backend cleanup**

~~~bash
git add graph_manager/ports.py graph_manager/domain/models.py pyproject.toml uv.lock tests/test_deepseek_harness_sdk.py
git commit -m "refactor: make Harness the only planning runtime"
~~~

### Task 5: Document the single runtime and final acceptance checks

**Files:**
- Modify: `README.md`
- Check: `skill_library/README.md`, `examples/harness-local-vlm.patch.yml`, `graph_manager/harness_profile/cordis.patch.yml`

- [x] **Step 1: Replace the outdated planning section**

Run this exact edit from the repository root. It preserves the Goal wording section below it:

~~~bash
.venv/bin/python - <<'PY'
from pathlib import Path

path = Path("README.md")
source = path.read_text(encoding="utf-8")
start = source.index("## Planning loop\n")
end = source.index("## Goal wording baseline\n", start)
replacement = '''## Planning loop

Graph Manager accepts a Goal, an optional scene image or observation text, and the complete public Skill Library. In the current version, one model response proposes all semantic Subgoals and one Skill Subgraph for each Subgoal. The application checks Skill IDs, Contract inputs, object references, dependencies, and DAG structure. It sends addressable validation feedback in the same DeepSeek Harness session when a proposal is invalid. It does not execute robot Skills.

DeepSeek Harness is the sole model runtime. It owns model access and conversation history; Graph Manager owns the planning input, the accepted JSON schema, Contract validation, and the decision to accept or request another proposal. The local model server, such as vLLM, is a separate process.

### Install and run

Create the isolated Python environment from the committed lock file:

```bash
uv sync --locked --extra dev
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Copy the local vision-model route and edit its `baseURL` and model ID to match the served model:

```bash
mkdir -p run
cp examples/harness-local-vlm.patch.yml run/local-vlm.patch.yml
```

The route declares `input: [text, image]` for the vision model. Harness uses YAML for its profile composition; Skill Contracts and task plans remain JSON. Supply the route credential through `LAB_VLM_API_KEY`; a dummy value is sufficient for an unauthenticated local endpoint.

```bash
export LAB_VLM_API_KEY=dummy
.venv/bin/graph-manager-plan \\
  --goal-file goal.txt \\
  --image scene.png \\
  --dsh-home run/dsh-home \\
  --provider lab-vlm \\
  --model Qwen/Qwen3.5-4B \\
  --patch run/local-vlm.patch.yml \\
  --output run/plan.json
```

The same command accepts `--observation-file`, `--state-file`, `--entity-catalog`, and `--max-attempts`. Run `graph-manager-plan --help` for all options. The default planner profile keeps local session persistence and compaction while disabling coding tools, workspace instructions, and the bundled DeepSeek telemetry contributors. The output records the Harness session ID. The pinned SDK stores session history under the selected `--dsh-home`; this version does not resume an existing ID from a later Python process.

The optional entity catalog gives exact bindable IDs and types:

```json
{"entities": [{"id": "apple", "types": ["MovableObject"]}]}
```

Without the catalog, the model receives no GT ID list; object references remain unresolved and the result status is `unresolved_references`. With it, `{"ref":"apple"}` must match an exact ID with a compatible Contract input type. The catalog must not contain evaluator truth.

### Plan format and checks

The model proposes one JSON object:

```json
{
  "schema_version": 1,
  "kind": "task_plan",
  "subgoals": [{"id": "sg_1", "goal": "Hold the apple"}],
  "subgraphs": [{
    "subgoal_id": "sg_1",
    "nodes": [{
      "id": "n1",
      "skill_id": "skill_004",
      "args": {"object": {"ref": "apple"}},
      "depends_on": []
    }]
  }]
}
```

Each Subgraph is a DAG for one Subgoal. Every Contract input key must appear; `OptionalVector2` may be `null`. A rejected proposal reports `code`, `path`, and `message`; for example, an unknown Skill ID points to `$.subgraphs[0].nodes[0].skill_id`. Output attempts and issues are retained.

An optional state file supplies explicitly observed facts:

```json
{"facts": [{"predicate": "gripper_empty", "args": {}, "value": false}]}
```

The validator checks only facts and input conditions represented in `checkable_requires`. Input-only requirements can be checked anywhere in the plan; observed facts apply only to initially ready nodes in the first Subgoal. Missing facts mean unknown. Other natural-language preconditions, physical execution, and final Goal completion require later observation and Verifiers.

### Code layout

```text
cli.py
  → PlanningService
      ├─ PlanningInputBuilder → initial turn / feedback turn
      ├─ DeepSeekHarnessSession → candidate plan
      └─ task_plan_validation → accepted plan / validation issues
```

| Directory or module | Responsibility |
| --- | --- |
| `application/input_builder.py` | Build first and corrective model turns |
| `application/planning_service.py` | Orchestrate proposals and bounded acceptance |
| `domain/` | Planning data and pure JSON, Contract, and DAG checks |
| `prompts/task_plan.py` | Model-visible plan instructions and feedback text |
| `adapters/` | DeepSeek SDK session and public JSON Skill Library loading |
| `cli.py`, `plan_inputs.py` | Read local inputs, construct dependencies, write results |

The execution runner for ZenoBench Skills and post-execution Verifiers is a separate future component.

'''
source = source[:start] + replacement + source[end:]
path.write_text(source, encoding="utf-8")
PY
~~~

- [x] **Step 2: Check the README and installed command**

~~~bash
rg -n 'graph-manager-plan-harness|Direct HTTP|OpenAICompatibleModel|HarnessPlanningService|PlanningLoop' README.md
.venv/bin/graph-manager-plan --help
git diff --check
~~~

Expected: `rg` returns no matches (exit 1), the sole CLI help prints its Harness arguments, and `git diff --check` exits 0.

- [x] **Step 3: Run final repository checks**

~~~bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -c 'from deepseek_harness import DeepSeekHarness; print(DeepSeekHarness.__name__)'
git status --short
~~~

Expected: tests end with `OK`; Ruff passes; SDK import prints `DeepSeekHarness`; `git status` lists the planned README change and, if the plan was not committed before worktree creation, the saved plan document. These checks prove the integration boundary and mock-session behavior; a live Qwen/vLLM image-to-plan run remains the next lab experiment.

- [x] **Step 4: Commit documentation**

~~~bash
git add README.md
git commit -m "docs: explain Harness-only planning architecture"
~~~

## Acceptance checklist

- One `graph-manager-plan` command constructs a DeepSeek Harness session and calls one `PlanningService`.
- The first model turn contains the Goal, public Library, optional observation/image/catalog/state, and plan-output instruction.
- Corrective turns contain only validation feedback; Harness retains the earlier turns.
- The domain validator still checks the same JSON schema, IDs, parameters, references, checkable conditions, and DAG structure.
- The public JSON Library and private Skill Contracts remain unchanged.
- Direct HTTP model code, Python conversation replay, duplicate planning services, and their installed CLI entry are gone.
- No robot Skill is executed by the planning command.
