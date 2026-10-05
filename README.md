# Graph Manager

Graph Manager focuses on task-conditioned skill graphs and the VLM interface around them. It uses visual observations, a user's task, and a skill library to propose semantic subgoals and a skill subgraph for each subgoal. This repository defines how those outputs are represented, parsed, and checked against existing skill contracts. The robot skills and benchmark scenes are maintained by collaborators in the same project.

## Architecture

These figures show the intended architecture. The current planning loop, described below, produces all Subgoals and Skill Subgraphs in one model response; the illustrated per-Subgoal execution and reassessment loop is the longer-term design.

[![Figure 1: Skill-graph-based agentic task execution](docs/diagrams/graph-manager-figure1.png)](docs/diagrams/graph-manager-figure1.svg)

*Figure 1. A VLM plans semantic Subgoals, proposes a Skill Subgraph for the current Subgoal, and uses observations after execution to decide what to do next.*

[![Figure 2: Skill Library as a semantic-to-policy interface](docs/diagrams/graph-manager-figure2.png)](docs/diagrams/graph-manager-figure2.svg)

*Figure 2. Skill IDs, descriptions, Contracts, conditional links, and fallback connect semantic planning to a uniform invocation interface. The policy families shown are illustrative backend examples, not current ZenoBench integrations.*

## Skill Library v1

The [Skill Library](skill_library/README.md) keeps one JSON Contract per task-level ZenoBench capability and generates one [complete public catalog](skill_library/skill_library.json). Its nine Skills are available for the model to select in a graph. The generated catalog includes conditional composition hints without implementation paths. The model will propose a new Skill DAG for each task. The current library is a documented interface and does not yet include a graph runner or independent visual verifiers.

Run `python3 skill_library/viewer/server.py` and open `http://127.0.0.1:8765` to browse the current library as a local, searchable Wiki-style page. Its overview draws all nine Skills and the 17 directed links represented by 10 documented connection groups. These are conditional composition hints, not an exhaustive transition graph or a runtime task DAG.

The [ZenoBench `skills.py` function inventory](docs/zenobench-skills-function-inventory.md) lists all 44 source callables and identifies the nine represented by task-level Skill Contracts. The other 35 are implementation details, not graph nodes.

## Planning loop

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

The [example route](examples/harness-local-vlm.patch.yml) declares `input: [text, image]` for the vision model. Replace its model ID with the value passed to `--model`. Harness uses YAML for its profile composition; Skill Contracts and task plans remain JSON. Supply the route credential through `LAB_VLM_API_KEY`; a dummy value is sufficient for an unauthenticated local endpoint.

```bash
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

The validator checks only facts and input conditions represented in `checkable_requires`. Input-only requirements can be checked anywhere in the plan; observed facts apply only to initially ready nodes in the first Subgoal. Missing facts mean unknown. Object-bound facts require an entity catalog to ground references to exact IDs; zero-argument facts can be checked without one. Other natural-language preconditions, physical execution, and final Goal completion require later observation and Verifiers.

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

## Goal wording baseline

The five tasks below provide paired goal descriptions for a future comparison. **Original instruction** preserves the English task instruction from ZenoBench verbatim. **Detailed goal** makes the existing success conditions and permitted alternatives explicit. It describes the desired result without prescribing a skill, execution sequence, or object location in a particular scene variant.

Both wordings are intended to be evaluated against the same ZenoBench success conditions. A later comparison should keep the scene variants, available skills, execution system, and evaluator fixed so that goal wording is the variable under study. The detailed wording does not reveal which optional objects are present in a particular scene.

### Collect fruits

**Original instruction**

> Collect the fruits and place them in a container on the low bookcase in the living room.

**Detailed goal**

> Place both the apple and the orange inside the same available container, either a fruit basket or a serving tray. Leave that container upright on the low bookcase in the living room. Leave all doors and drawers closed. Do not leave any task object that began more than 10 cm above the floor lying on the floor, unless it is inside a container.

### Tidy toys

**Original instruction**

> Collect the toys and store them in the toy box.

**Detailed goal**

> Place the toy car, toy block, and rubber duck inside the same available container, either the toy box or a storage basket. Leave the chosen container upright. Leave all doors and drawers closed. Do not leave any task object that began more than 10 cm above the floor lying on the floor, unless it is inside a container.

### Shelve books

**Original instruction**

> Collect the books and place them on the bookshelf.

**Detailed goal**

> Place both books on a bookcase. Each book may be on either available bookcase, on its top or on a shelf level. Leave all doors and drawers closed. Do not leave any task object that began more than 10 cm above the floor lying on the floor, unless it is inside a container.

### Set up breakfast

**Original instruction**

> Set up the dining table for breakfast.

**Detailed goal**

> Arrange a breakfast place setting on the dining table with one plate or bowl, one cup or mug, and a spoon. Keep the selected plate or bowl and the selected cup or mug upright. All three selected items must be on the dining table and within 0.5 m of one another. Leave all doors and drawers closed. Do not leave any task object that began more than 10 cm above the floor lying on the floor, unless it is inside a container.

### Prepare the study desk

**Original instruction**

> Prepare the study desk with a notebook, a pen, and a mug.

**Detailed goal**

> Place a notebook, either a pen or a pencil, and either a mug or a cup on the study desk. Keep the selected mug or cup upright. Leave all doors and drawers closed. Do not leave any task object that began more than 10 cm above the floor lying on the floor, unless it is inside a container.
