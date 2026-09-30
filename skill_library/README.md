# Skill Library v1

This directory contains the first model-facing capability library for the skills currently implemented in ZenoBench. It is a contract catalog, not a collection of task plans. ZenoBench already has executable functions, scene annotations, a scripted task policy, and evaluation rules; it does not supply this contract catalog or reusable task-conditioned Skill DAGs.

## Files and boundaries

- `catalog.yaml` is the complete public catalog supplied to the model in v1. `id` is an opaque stable identifier. `name` and `description` carry the capability semantics. A future second implementation of `pick` can have a different `id` and a similar `name` without changing the graph schema.
- `connections.yaml` supplies conditional composition hints to the model. A hint identifies a possible transition between capability types. It does not assert that every scene permits the transition or prescribe a task DAG.
- `runtime_bindings.yaml` records the corresponding ZenoBench executor and currently available simulator-side result check. It stays outside the model prompt. The full conceptual Contract is the public entry plus the runtime binding with the same `id`.

The model proposes a task graph with node IDs, referenced Skill IDs, concrete arguments, and dependencies. The future graph runner will validate references, parameter shapes, and acyclicity; check the current preconditions before each call; invoke the bound executor; then observe the result. The model supplies the semantic dependency edges. No programmatic proof of why an edge makes sense is assumed here.

## Scope and evidence

The catalog covers the public navigation, articulated-part, pick, push, and placement functions, plus the two microwave-specific functions used by the current scripted policy. `place` into a container and `place_on` a surface have separate public Contracts because they expose different goals and checks. `pick_flat` and `place_flat` remain internal execution strategies. Most manipulation skills navigate to a working pose internally; an explicit navigation node is therefore optional.

The conditions in the public entries come from `zeno_skills/skills.py`, `zeno_skills/task_policy.py`, and scene/asset annotations. Some are checked directly by the existing functions. Others, such as a free gripper before handle manipulation or a door being open before accessing an enclosed object, are enforced by the scripted policy or must be checked by a future graph runner. They are not claimed to be implemented preflight checks in this repository.

`connections.yaml` uses `basis: scripted_policy` when the current policy actually uses the composition, `basis: internal_pick_strategy` for the push inside flat-object picking, and `basis: implementation` for optional explicit navigation. These labels describe source evidence, not a runtime success guarantee. No existing ZenoBench task trajectory is copied as a reusable graph.

Current verifiers use privileged simulator state and annotations. An independent visual or real-robot verifier and a graph runner are outside this v1 library. In particular, starting microwave heating does not by itself establish a target food temperature, and the microwave door-cycle implementation contains a fixed inspection pose that needs generalization before deployment to arbitrary scenes.

## Source references

- ZenoBench `zeno_skills/skills.py`: implementations and internal result checks.
- ZenoBench `zeno_skills/task_policy.py`: actual task-level skill compositions and access handling.
- ZenoBench `zeno_skills/annotations.py` and `tasks/*/annotation.json`: supported object, surface, and articulated-part metadata.
- ZenoBench `tools/run_skills.py`: directly exposed generic CLI operations.
