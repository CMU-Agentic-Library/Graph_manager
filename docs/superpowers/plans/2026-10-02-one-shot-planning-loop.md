# One-shot Planning Loop Implementation Plan

> **For agentic workers:** Use the test-driven-development workflow to implement each task inline. The user has already requested this refactor.

**Goal:** Generate a complete task plan in one model response, return precise validation feedback in the same conversation, and keep planning layers separately maintainable.

**Architecture:** A small application loop owns conversation state and retries. Pure domain validation checks model proposals against JSON Skill Contracts and optional facts. Prompts and external adapters live in separate modules.

**Tech Stack:** Python 3.12, standard library, unittest, Ruff, JSON.

---

### Task 1: Complete task-plan validation

**Files:** Create `tests/test_task_plan_validation.py` and `graph_manager/domain/task_plan_validation.py`; move pure logic from `graph_manager/validation.py` to `graph_manager/domain/validation.py`; create `graph_manager/domain/models.py`.

- [x] Write tests that submit a full `task_plan` and assert an exact path such as `$.subgraphs[0].nodes[0].skill_id` for an unknown Skill ID.
- [x] Run the focused tests and confirm failure because the new entry point does not exist.
- [x] Implement `validate_task_plan(raw: str, library: dict, catalog: EntityCatalog | None, state: ObservedState | None) -> dict`; reuse and adapt existing ID, type, dependency, and cycle checks.
- [x] Add `checkable_requires` to applicable Skill Contracts and catalog generation. Include input `nonzero_vector` and state-fact checks, with tests proving missing facts are not failures and later nodes are not checked against initial state.
- [x] Run the focused tests and the existing validation tests.

### Task 2: Conversation and repair loop

**Files:** Create `tests/test_planning_loop.py`, `graph_manager/application/conversation.py`, `graph_manager/application/planning_loop.py`, `graph_manager/prompts/task_plan.py`, and `graph_manager/ports.py`.

- [x] Write a fake-model test whose first reply has an unknown Skill ID and whose second reply is valid; assert the second request contains the original task context, the first raw response, and a JSON feedback record with the exact error path.
- [x] Run the focused tests and confirm failure before implementation.
- [x] Implement `PlanningLoop.run(request)` with a positive, bounded `max_attempts`; a valid first output takes one model call, a rejected final attempt returns recorded issues and attempts.
- [x] Keep prompt construction and feedback formatting out of the loop module; preserve raw outputs for debugging.
- [x] Run focused tests.

### Task 3: Adapters and CLI

**Files:** Move `graph_manager/openai_compatible.py` and `graph_manager/repository.py` to `graph_manager/adapters/`; update `graph_manager/cli.py`, `tests/test_openai_compatible.py`, and `tests/test_planner_cli.py`.

- [x] Write a fake HTTP test that checks the adapter sends the full role-ordered message history with an image in the initial user message.
- [x] Run focused adapter tests and confirm the new interface fails.
- [x] Implement the message-list adapter and CLI wiring for `--max-attempts` and optional `--state-file`.
- [x] Run focused tests, then all tests and Ruff.

### Task 4: Documentation and final verification

**Files:** Update `README.md` and `skill_library/README.md`.

- [x] Document the one-shot JSON shape, the repair loop, the structured state facts, and the precise boundary of precondition checks.
- [x] Verify generated `skill_library/skill_library.json` is fresh and contains all nine Skills.
- [x] Run `.venv/bin/python -m unittest discover -s tests -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and inspect `git diff --check`.
