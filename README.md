# Graph Manager

Graph Manager focuses on task-conditioned skill graphs and the VLM interface around them. It uses visual observations, a user's task, and a skill library to propose semantic subgoals and a skill subgraph for each subgoal. This repository defines how those outputs are represented, parsed, and checked against existing skill contracts. The robot skills and benchmark scenes are maintained by collaborators in the same project.

## Skill Library v1

The [Skill Library](skill_library/README.md) keeps one JSON Contract per task-level ZenoBench capability and generates one [complete public catalog](skill_library/skill_library.json). Its nine Skills are available for the model to select in a graph. The generated catalog includes conditional composition hints without implementation paths. The model will propose a new Skill DAG for each task. The current library is a documented interface and does not yet include a graph runner or independent visual verifiers.

Run `python3 skill_library/viewer/server.py` and open `http://127.0.0.1:8765` to browse the current library as a local, searchable Wiki-style page. Its overview draws all nine Skills and the 17 directed links represented by 10 documented connection groups. These are conditional composition hints, not an exhaustive transition graph or a runtime task DAG.

The [ZenoBench `skills.py` function inventory](docs/zenobench-skills-function-inventory.md) lists all 44 source callables and identifies the nine represented by task-level Skill Contracts. The other 35 are implementation details, not graph nodes.

## Planner v1

The planner now accepts a goal, an optional current image or observation text, and the complete public Skill Library. It asks a VLM for all semantic Subgoals first, then asks for one Skill Subgraph per Subgoal. The JSON proposals are checked against the nine public Skill IDs, Contract input names and types, local dependencies, and DAG structure. The planner saves the raw model responses with the validation result; it does not execute robot Skills.

Create the isolated Python environment from the committed lock file with `uv`, then run the tests:

```bash
uv sync --extra dev
.venv/bin/python -m unittest discover -s tests
.venv/bin/ruff check graph_manager tests/test_planner_*.py tests/test_openai_compatible.py
.venv/bin/ruff format --check graph_manager tests/test_planner_*.py tests/test_openai_compatible.py
```

If `uv` is unavailable, `python3 -m venv .venv` followed by `.venv/bin/python -m pip install -e '.[dev]'` also works.

For a local VLM served through a vLLM OpenAI-compatible endpoint, run:

```bash
.venv/bin/graph-manager-plan \
  --goal-file goal.txt \
  --image scene.jpg \
  --base-url http://127.0.0.1:8000/v1 \
  --model YOUR_SERVED_VLM_NAME \
  --output run/plan.json
```

Add `--entity-catalog entities.json` to give the model a GT list of bindable IDs and types. Its format is:

```json
{"entities": [{"id": "apple", "types": ["MovableObject"]}]}
```

The catalog is optional. Without it, the model receives no ID list, and object references remain unresolved; the result status is `unresolved_references`. With it, `{"ref":"apple"}` must match an exact ID and a compatible Contract input type. GT catalog data should contain only IDs and types, not final evaluator truth. A later grounding adapter can resolve references from vision while keeping the graph JSON shape. An observation text file can be supplied with `--observation-file`, and `GRAPH_MANAGER_API_KEY` supplies an optional endpoint token. Run `graph-manager-plan --help` for all flags.

The model's first response has `schema_version`, `kind: "subgoal_plan"`, and a `subgoals` array of `{id, goal}`. Each following response has `kind: "skill_subgraph"`, `subgoal_id`, and `nodes` of `{id, skill_id, args, depends_on}`. Each graph is a DAG for one Subgoal. `OptionalVector2` inputs must still be present as a key and may have value `null`. Static checks do not prove physical preconditions, successful execution, or the final task goal; those belong to the future Runner and Verifiers.

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
