---
name: dip-utensil
description: "Lower a held spoon's far end into a container below its rim, hold it there and lift it out."
---

# Dip a utensil (`skill_069`)

`dip(tool: tool_ref, container: container_ref)`

Lower a held spoon's far end into a container below its rim, hold it there and lift it out.

## When to use

A held utensil must go into a container briefly (taste, wet).

## Not to be confused with

- `stir`: stir circles inside the container; dip goes in and out once.

## Inputs

- `tool` (`tool_ref`): The held utensil.
- `container` (`container_ref`): The pot or bowl.

## Applicability

Requires holding(hand=right, object=$tool); base_near(place=$container); uncovered(container=$container).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$container)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `uncovered(container=$container)` — No lid rests on the container rim. GT: object_pose, container_profile, asset_tags.

## Postconditions (verified on live GT state)

- `dipped(container=$container)` — A held utensil tip entered the container below its rim and came back out. GT: robot_memory (tool-tip samples).
- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `dipped(container=$container)` (all paths)
- `holding(hand=right, object=$tool)` (all paths)

## Policy paths (first match on the bound nouns)

### `tip_below_rim` — when 'utensil' in tool.tags

1. `policy_113($tool, $container)`

## Relations

- Next step: `stir` (`skill_038`) (enables) — the utensil then stirs
- Alternative: `stir` (`skill_038`) — the contents must be mixed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_077`.
