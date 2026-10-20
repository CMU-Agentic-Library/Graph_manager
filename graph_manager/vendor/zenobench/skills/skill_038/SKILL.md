---
name: stir-container
description: "Dip a held spoon's far end into a container and move it in a circle below the rim; succeeds after one full turn inside."
---

# Stir a container (`skill_038`)

`stir(container: container_ref, tool: tool_ref)`

Dip a held spoon's far end into a container and move it in a circle below the rim; succeeds after one full turn inside.

## When to use

The contents of a container must be stirred with a held utensil.

## Not to be confused with

- `dip`: dip goes in and out without circling.

## Inputs

- `container` (`container_ref`): The pot or bowl to stir.
- `tool` (`tool_ref`): The held utensil (spoon).

## Outputs

- `turns` (`number`): Measured turns of the tip inside the container.

## Applicability

Requires holding(hand=right, object=$tool); base_near(place=$container); uncovered(container=$container).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$container)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `uncovered(container=$container)` — No lid rests on the container rim. GT: object_pose, container_profile, asset_tags.

## Postconditions (verified on live GT state)

- `stirred(container=$container)` — A held utensil tip completed one full circle inside the container below its rim. GT: robot_memory (tool-tip samples).
- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `stirred(container=$container)` (all paths)
- `holding(hand=right, object=$tool)` (all paths)

## Policy paths (first match on the bound nouns)

### `circle_below_rim` — when 'utensil' in tool.tags

1. `policy_085($tool, $container)`

## Relations

- Previous step: `brace` (`skill_027`) (then) — the braced container is stirred
- Previous step: `pour` (`skill_039`) (enables) — the poured food is stirred
- Previous step: `uncover` (`skill_046`) (enables) — the opened pot is stirred
- Previous step: `dip` (`skill_069`) (enables) — the utensil then stirs
- Next step: `cover` (`skill_045`) (enables) — the pot is covered again
- Next step: `heat` (`skill_043`) (then) — the stirred food is heated
- Fallback on failure: `brace` (`skill_027`) (recover) — the container slides while stirring
- Alternative: `dip` (`skill_069`) — the contents must be mixed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_046`.
