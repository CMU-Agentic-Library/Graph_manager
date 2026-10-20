---
name: hover-object
description: Hold the carried object centred 6 cm above a target (a container opening, a spot on a surface) without releasing it, e.g. to show or to align before a drop.
---

# Hover a held object over a target (`skill_063`)

`hover(object: object_ref, target: entity_ref)`

Hold the carried object centred 6 cm above a target (a container opening, a spot on a surface) without releasing it, e.g. to show or to align before a drop.

## When to use

A held object must be positioned over a target before dropping or pouring.

## Not to be confused with

- `drop`: hover keeps the grasp.
- `lift`: lift has no target point.

## Inputs

- `object` (`object_ref`): The right-held object.
- `target` (`entity_ref`): What to hover over.

## Applicability

Requires holding(hand=right, object=$object); base_near(place=$target).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$target)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `hovering_over(object=$object, target=$target)` — The right-held object's bottom is 3-15 cm above the target's top, centred within 4 cm. GT: object_pose, gripper_state, asset_annotation.
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `hovering_over(object=$object, target=$target)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `above_target` — when always (default path)

1. `policy_115($object, $target)`

## Relations

- Next step: `drop` (`skill_019`) (enables) — the object is released into the container under it
- Next step: `release` (`skill_021`) (enables) — the object is let go right there
- Alternative: `lift` (`skill_023`) — only a height matters

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_071`.
