---
name: square-object
description: "Align an object's edges with its support's edges (yaw within 5 deg): pick it, turn it by the measured yaw error and set it back down at the same spot."
---

# Square an object (`skill_064`)

`square(object: object_ref)`

Align an object's edges with its support's edges (yaw within 5 deg): pick it, turn it by the measured yaw error and set it back down at the same spot.

## When to use

An object must be rotated so its sides align with the support edges.

## Not to be confused with

- `rotate`: rotate turns a held object by a requested angle; square finds the angle itself.

## Inputs

- `object` (`object_ref`): An object resting on a support.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `squared(object=$object)` — Object yaw within 5 deg of the support's axes (edges parallel), resting on a support. GT: object_pose, support_annotation.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `squared(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `pick_rotate_place` — when 'top_pinch' in object.grasp_types

1. `policy_108($object) as sq`
2. `policy_010($object)`
3. `policy_075($object, #sq.degrees)`
4. `policy_015($object, @object.support, hint=#sq.xy)`

## Relations

- Next step: `stack` (`skill_020`) (then) — squared blocks stack cleanly
- Alternative: `rotate` (`skill_025`) — the object is already in the hand

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_072`.
