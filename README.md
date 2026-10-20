# Graph Manager

Graph Manager focuses on task-conditioned skill graphs and the VLM interface around them. It uses visual observations, a user's task, and a skill library to propose semantic subgoals and a skill subgraph for each subgoal. This repository defines how those outputs are represented, parsed, and checked against existing skill contracts. The robot skills and benchmark scenes are maintained by collaborators in the same project.

## Architecture

These figures show the intended architecture. The current planning loop, described below, produces all Subgoals and Skill Subgraphs in one model response; the illustrated per-Subgoal execution and reassessment loop is the longer-term design.

[![Figure 1: Skill-graph-based agentic task execution](docs/diagrams/graph-manager-figure1.png)](docs/diagrams/graph-manager-figure1.svg)

*Figure 1. A VLM plans semantic Subgoals, proposes a Skill Subgraph for the current Subgoal, and uses observations after execution to decide what to do next.*

[![Figure 2: Skill Library as a semantic-to-policy interface](docs/diagrams/graph-manager-figure2.png)](docs/diagrams/graph-manager-figure2.svg)

*Figure 2. Skill IDs, descriptions, Contracts, conditional links, and fallback connect semantic planning to a uniform invocation interface. The policy families shown are illustrative backend examples, not current ZenoBench integrations.*

## Skill Library

Skills come from [ZenoBench](https://github.com/CMU-Agentic-Library/ZenoBench), which provides the underlying robot skills and the environment service. Graph Manager keeps no skill definitions of its own. `scripts/sync_zenobench.py` copies `skill_library/skills/*/{SKILL.md,skill.json}` and `tasks.json` from a local ZenoBench checkout into `graph_manager/vendor/zenobench/` and records the commit in `COMMIT`. The 35 reference subgraphs from `skill_library/plans/` go to `tests/fixtures/zenobench_plans/` and are used only as test data.

```bash
git -C ../ZenoBench checkout <commit>
.venv/bin/python scripts/sync_zenobench.py ../ZenoBench
```

The model sees the skills through DeepSeek Harness's skill loader: the catalog lists each skill's `name` and `description`, and the model loads a full `SKILL.md` when it needs one. The validator reads the matching `skill.json` files.

## Planning

Graph Manager accepts a Goal, an optional scene image, and optional observation text. One model response proposes all Subgoals and one ZenoBench schema 2 skill subgraph for each Subgoal:

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

### Install and run

```bash
uv sync --locked --extra dev
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Copy the local vision-model route and edit its `baseURL` and model ID to match the served model. Skill loading is a tool call, so the served model must support tool calling (for vLLM, `--enable-auto-tool-choice` with the model's `--tool-call-parser`).

```bash
mkdir -p run
cp examples/harness-local-vlm.patch.yml run/local-vlm.patch.yml
export LAB_VLM_API_KEY=dummy
.venv/bin/graph-manager-plan \
  --goal-file goal.txt \
  --image scene.png \
  --dsh-home run/dsh-home \
  --provider lab-vlm \
  --model YOUR_SERVED_VLM_NAME \
  --patch run/local-vlm.patch.yml \
  --output run/plan.json
```

The output records the plan, every attempt, the ZenoBench commit, and the Harness session ID.

## Execution

`adapters/env_http.py` is the client for the ZenoBench environment service (interface v2: `initial_task`, `do_contract`, `check_task`, `observe`). `application/execution/graph_executor.py` runs one validated subgraph: it sends nodes in dependency order as `do_contract` batches, starts a new batch when a node reads a `from` output of the current batch, fills that output from the earlier reply, and stops at the first failed contract. The closed loop that replans after each Subgoal is the next step.

### Code layout

| Directory or module | Responsibility |
| --- | --- |
| `domain/` | Pure data and rules: skill types, subgraph and task plan checks, environment data types |
| `ports.py` | Interfaces to the model session, skill library, and environment |
| `adapters/` | DeepSeek Harness session, ZenoBench library files, environment HTTP client |
| `application/execution/` | Execution layer: subgraph to contract batches |
| `application/planning_service.py`, `application/input_builder.py`, `prompts/` | One-shot planning with validation feedback |
| `cli.py`, `plan_inputs.py` | Read local inputs, construct dependencies, write results |
