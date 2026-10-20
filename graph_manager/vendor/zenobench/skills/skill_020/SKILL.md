---
name: stack-object
description: Set the held object centred on the top face of another object (block on block, plate on plate).
---

# Stack an object on another (`skill_020`)

`stack(object: object_ref, base: object_ref)`

Set the held object centred on the top face of another object (block on block, plate on plate).

## When to use

A held object must be put on top of another object.

## Not to be confused with

- `place`: place targets a support or container; stack targets the top face of an object.

## Inputs

- `object` (`object_ref`): The held object.
- `base` (`object_ref`): The object to stack onto.

## Applicability

Requires holding(hand=right, object=$object); base_near(place=$base); top_clear(object=$base).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$base)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `top_clear(object=$base)` — No other object rests on the object's top face. GT: object_pose, asset_annotation.

## Postconditions (verified on live GT state)

- `on_top_of(object=$object, base=$base)` — Object rests on the base object's top face: bottom within 2 cm of it, centre over its footprint. GT: object_pose, asset_annotation.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `on_top_of(object=$object, base=$base)` (all paths)
- `hand_empty(hand=right)` (all paths)

## May invalidate

`holding(right,$object)`, `top_clear($base)`

## Policy paths (first match on the bound nouns)

### `top_face` — when always (default path)

1. `policy_074($object, $base)`

## Relations

- Previous step: `square` (`skill_064`) (then) — squared blocks stack cleanly
- Next step: `pick` (`skill_017`) (enables) — a taller stack is built
- Fallback on failure: `pick` (`skill_017`) (recover) — the base's top is occupied: remove the top object first
- Alternative: `place` (`skill_018`) — a support surface is acceptable instead

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_028`.
