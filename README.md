# Graph Manager

Graph Manager focuses on task-conditioned skill graphs and the VLM interface around them. It uses visual observations, a user's task, and a skill library to propose semantic subgoals and a skill subgraph for each subgoal. This repository defines how those outputs are represented, parsed, and checked against existing skill contracts, and executes them against the ZenoBench environment service. The robot skills and benchmark scenes are maintained by collaborators in the same project.

## Architecture

These figures show the architecture. `graph-manager-plan` produces all Subgoals and Skill Subgraphs in one model response. `graph-manager-run` executes one Subgoal at a time and lets the model continue, replan, or finish after each one (see Closed-loop runs). Conditional links and fallback in Figure 2 are not implemented yet.

[![Figure 1: Skill-graph-based agentic task execution](docs/diagrams/graph-manager-figure1.png)](docs/diagrams/graph-manager-figure1.svg)

*Figure 1. A VLM plans semantic Subgoals, proposes a Skill Subgraph for the current Subgoal, and uses observations after execution to decide what to do next.*

[![Figure 2: Skill Library as a semantic-to-policy interface](docs/diagrams/graph-manager-figure2.png)](docs/diagrams/graph-manager-figure2.svg)

*Figure 2. Skill IDs, descriptions, Contracts, conditional links, and fallback connect semantic planning to a uniform invocation interface. The policy families shown are illustrative backend examples, not current ZenoBench integrations.*

## Skill Library

Skills come from [ZenoBench](https://github.com/CMU-Agentic-Library/ZenoBench), which provides the underlying robot skills and the environment service. Graph Manager keeps no skill definitions of its own. `scripts/sync_zenobench.py` copies `skill_library/skills/*/{SKILL.md,skill.json}` from a local ZenoBench checkout into `graph_manager/vendor/zenobench/`, records the commit in `COMMIT`, and writes `tasks.json`: an index of both task catalogs (`skill_library/tasks.json` and `benchmark/v3/tasks.json`) with each task's ID, catalog, default profile, and variant difficulties. Goals, routes, and variant descriptions are not copied, because the benchmark must not show them to the planner. The 35 reference subgraphs from `skill_library/plans/` go to `tests/fixtures/zenobench_plans/` and are used only as test data.

```bash
git -C ../ZenoBench checkout <commit>
.venv/bin/python scripts/sync_zenobench.py ../ZenoBench
```

The model sees the skills through DeepSeek Harness's skill loader: the catalog lists each skill's `name` and `description`, and the model loads a full `SKILL.md` when it needs one. The validator reads the matching `skill.json` files.

## Planning

Graph Manager accepts a Goal, an optional scene image, and optional observation text. The model proposes all Subgoals and one ZenoBench schema 2 skill subgraph for each Subgoal, and submits them as the arguments of a tool call:

```json
{
  "schema_version": 2,
  "kind": "task_plan",
  "subgoals": [{"id": "sg_1", "goal": "Hold the apple"}],
  "subgraphs": [{
    "schema_version": 2,
    "kind": "skill_subgraph",
    "subgoal_id": "sg_1",
    "nodes": [{"id": "n1", "skill": "pick", "args": {"object": {"ref": "apple"}}, "depends_on": []}]
  }]
}
```

An argument is `{"ref": scene name}`, `{"value": literal}`, or `{"from": "<node>.<output>"}` for a measured output of an ancestor node in the same subgraph. The validator applies the rules of ZenoBench `skill_library/graph.py` (skill verb, required and allowed inputs, value types, `from` references, DAG) and reports every issue with a JSON path, such as `$.subgraphs[0].nodes[0].skill`. It does not check whether a scene name exists or whether preconditions hold; the environment decides both. Rejected proposals receive the issues as feedback in the same Harness session.

The model hands in every answer by calling one of two tools from a small MCP server (`adapters/submit_tools.py`) that each Harness session starts: `submit_plan` takes a task plan, and in the closed loop `submit_decision` takes `{"kind": "continue"}` or `{"kind": "finish"}`. The tools' JSON Schemas (`domain/submission.py`) fix the field names, the argument forms, and the skill verbs. vLLM started with `--tool-strict-level parameter` generates tool arguments that always match them, so an answer is never malformed JSON. `submit_plan` runs the validator inside the tool and returns every issue as a tool error, so the model can fix a plan within the same turn.

### Install and run

```bash
uv sync --locked --extra dev
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Skill loading is a tool call, so the served model must support tool calling (for vLLM, `--enable-auto-tool-choice` with the model's `--tool-call-parser`, plus `--tool-strict-level parameter` so that tool arguments follow their schemas). `examples/vllm-qwen3.5-4b.compose.yml` serves Qwen3.5-4B this way on port 8001 as `qwen3.5-4b`, and `examples/harness-local-vlm.patch.yml` points Harness at that server. For another model, edit the patch's `baseURL` and model ID; `--model` must match the model ID.

```bash
mkdir -p run
cp examples/harness-local-vlm.patch.yml run/local-vlm.patch.yml
export LAB_VLM_API_KEY=dummy
.venv/bin/graph-manager-plan \
  --goal-file goal.txt \
  --image scene.png \
  --dsh-home run/dsh-home \
  --provider lab-vlm \
  --model qwen3.5-4b \
  --patch run/local-vlm.patch.yml \
  --output run/plan.json
```

The output records the plan, every attempt, the ZenoBench commit, and the Harness session ID.

## Closed-loop runs

`graph-manager-run` runs tasks against the ZenoBench environment service (interface v3). For each task and seed it calls `initial_task` with the profile, variant or difficulty, and seed, asks the model for a complete plan, and runs one Subgoal at a time. After each Subgoal the model receives every contract result (error codes and false conditions explained in plain language, with how to recover from `NOT_OBSERVED`, `NOT_IN_VIEW`, and `NOT_FOUND`), the new camera images, and the observation fields the profile turned on: scene objects (`gt`), or objects in view, objects seen earlier, and known places (`benchmark`), plus the robot state. Coordinates are left out, because skills take scene names; an observation field Graph Manager does not know is shown as compact JSON. It replies with `{"kind": "continue"}`, a `task_plan` for the remaining work, or `{"kind": "finish"}`; `continue` is refused after a failure and when no Subgoal remains. The run ends with `check_task`. The evaluator's `task_status` is logged but never shown to the model.

```bash
.venv/bin/python scripts/smoke_env.py --env-url http://HOST:8800 probe   # reachability, no simulator
export LAB_VLM_API_KEY=dummy
.venv/bin/graph-manager-run --all --env-url http://HOST:8800 --out runs/2026-10-21 \
  --dsh-home run/dsh-home --provider lab-vlm --model qwen3.5-4b \
  --patch run/local-vlm.patch.yml
# benchmark tasks, medium variants picked by seed, evaluation seeds 10-19
.venv/bin/graph-manager-run --all --catalog benchmark/v3/tasks.json --difficulty medium \
  --seed 10-19 --env-url http://HOST:8800 --out runs/2026-10-22-bench \
  --dsh-home run/dsh-home --provider lab-vlm --model qwen3.5-4b \
  --patch run/local-vlm.patch.yml
.venv/bin/graph-manager-summary runs/2026-10-22-bench --by difficulty --by variant
```

`--env-url` defaults to `$ZENOBENCH_ENV_URL`. `--env-profile` names any profile the service offers (`gt`, `benchmark`, `gt_sticky`, ...) and defaults to the profile of the task's catalog; the service answers an unknown one with `400 UNKNOWN_PROFILE`; `--variant` names one variant, `--difficulty` lets the service pick one of that tier by seed (tasks without that tier are skipped), and `--seed` takes a seed or a range and repeats. Each request gets `<task_id>/<profile>/<variant, difficulty-<tier>, or any>/seed_<seed>/` with `result.json` and one `attempt_N/` directory per exp holding `trajectory.jsonl` and the camera images in `images/`. `result.json` keeps the request, the profile, `check_task`'s `goal`, `dropped`, and `episode` as sent, the end reason, and counts of replans, subgoal runs, contract calls, model turns, and invalid replies. `graph-manager-summary RUN_DIR [--by KEY]` reads those files at any time and writes `summary.json`; `graph-manager-run` calls it at the end, grouped by profile and difficulty. The environment's own statistics (SPL, side effects) come from ZenoBench `benchmark/evaluate.py` over the service's `runs/env_service`. Rerunning the same command keeps decided runs and reruns errors; a rerun starts again at `attempt_1/` and appends to the existing `trajectory.jsonl`. A task whose model call fails without any output (a timeout, an unreachable model server) is recorded as an error, not a failure, so it is rerun as well. A `400` reply (unknown task, variant, or profile) is an error and is not retried. Any other environment error except `503 BUSY` (a released exp, a crash, a timeout, a transport error) restarts the task in a new exp and a new Harness session (at most twice); `503 BUSY` is retried every 30 seconds for up to 15 minutes.

`adapters/env_http.py` is the environment client. `application/execution/graph_executor.py` sends a Subgoal's nodes in dependency order as `do_contract` batches and fills `from` arguments from earlier outputs. `application/orchestration/` holds the episode loop, the batch runner, and the trajectory records.

### Code layout

| Directory or module | Responsibility |
| --- | --- |
| `domain/` | Pure data and rules: skill types, subgraph and task plan checks, environment data types |
| `ports.py` | Interfaces to the model session, skill library, and environment |
| `adapters/` | DeepSeek Harness session, ZenoBench library files, environment HTTP client |
| `application/execution/` | Execution layer: subgraph to contract batches |
| `application/planning_service.py`, `application/input_builder.py`, `prompts/task_plan.py` | One-shot planning with validation feedback |
| `cli.py`, `plan_inputs.py` | Read local inputs, construct dependencies, write results |
| `application/orchestration/`, `prompts/episode.py` | Orchestration layer: closed-loop episodes and their prompts, batch runs, trajectory records |
| `harness_profile/`, `vendor/zenobench/` | Harness profile patch; vendored ZenoBench skills and task index |
| `run_cli.py`, `harness_args.py` | `graph-manager-run` and the Harness options both commands share |
| `summary.py` | `graph-manager-summary`: statistics from the `result.json` files of a run directory |
| `domain/submission.py`, `adapters/submit_tools.py` | Submit tools: argument schemas and the stdio MCP server each Harness session starts |
