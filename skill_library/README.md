# Skill Library v1

## Which file is the library?

[`skill_library.yaml`](skill_library.yaml) is the **complete model-facing Skill Library** for v1. Give this one file to the model together with the current observation and task goal. It contains all nine public skills, their shared input types, and conditional composition hints. A task DAG is a separate output proposed by the model for one task.

[`skills/`](skills/) contains **one authoritative Contract YAML per Skill**. Edit these files when a capability changes. Each has `id`, `name`, `description`, `inputs`, `requires`, `achieves`, `outcomes`, `executor`, and `verifier`, plus optional outgoing `connections`. The opaque `id` identifies the exact Skill; `name` and `description` convey its meaning. Two future implementations can share a similar name and have different IDs.

The [`build.rb`](build.rb) generator reads the per-Skill Contracts and the shared [`types.yaml`](types.yaml) glossary, then writes `skill_library.yaml`. Run `ruby skill_library/build.rb` after editing a Contract. It removes `executor`, `verifier`, and evidence labels from the model-facing file, so the model receives the complete **public capability catalog** without code paths. The source Contracts remain the full internal library.

## What a connection means

A `connections` entry is a conditional hint between Skill types, not an existing task graph. ZenoBench already has executable functions and a scripted task policy, but it does not have a reusable Contract library or a model-produced DAG. We use the policy and implementation to document useful compositions; we do not copy its trajectories into fixed task graphs. The model chooses nodes and dependencies for the current task. The future graph runner will check references, input shapes, and cycles, then check real preconditions and outcomes during execution. It does not need to prove the model's semantic reason for each edge.

The source Contract's `basis` records where a hint came from: `scripted_policy` for a composition used by the current policy, `internal_pick_strategy` for the flat-object push within pick, and `implementation` for optional explicit navigation. A documented hint does not guarantee success in every scene. In particular, `pick` already handles its own edge-push strategy, so an extra `push` node should only appear when a separate repositioning step is intended.

## Current limits

The public requirements are grounded in ZenoBench `zeno_skills/skills.py`, `zeno_skills/task_policy.py`, and scene/asset annotations. Some are checked inside a Skill; others are currently enforced by the scripted policy and still need graph-runner preflight checks. Existing result checks use privileged simulator state and annotations. An independent visual verifier and graph runner are not part of this library. Starting microwave heating does not establish the final food temperature. The microwave inspection Skill also uses a fixed pose and needs generalization for arbitrary scenes.

Run `ruby tests/test_skill_library.rb` to check that the generated public file stays in sync with the source Contracts and contains no executor code paths.

## Browse the current library

From the repository root, run:

```bash
python3 skill_library/viewer/server.py
```

Open `http://127.0.0.1:8765` in a browser. The local page shows a searchable Skill index, each Contract's public fields, a type glossary, and clickable conditional connections. It reads `skill_library.yaml` on every refresh and checks for source Contract changes before serving it. The page polls every five seconds and also has a manual Refresh button. The viewer uses Python and Ruby standard libraries and does not send the library to an external service.

The nine Contracts cover the current task-level public capabilities in ZenoBench `zeno_skills/skills.py`, including the two microwave-specific actions used by the scripted policy. They are not an inventory of every helper function: `pick_flat` and `place_flat` are internal strategies, and the two placement Contracts describe different public goals over the existing placement functions. No standalone Skill currently represents waiting until food reaches a target temperature.

For the complete function-by-function inventory of `skills.py`, including internal and nested functions, see [ZenoBench function inventory](../docs/zenobench-skills-function-inventory.md).
