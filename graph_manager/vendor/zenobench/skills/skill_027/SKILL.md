---
name: brace-object
description: "Pinch a resting container with the left gripper so it cannot slide while the right hand stirs, wipes or pours into it."
---

# Brace an object with the left hand (`skill_027`)

`brace(object: object_ref)`

Pinch a resting container with the left gripper so it cannot slide while the right hand stirs, wipes or pours into it.

## When to use

An object must be held still by the left hand while the right hand works on it.

## Not to be confused with

- `pick`: brace leaves the object on its support.

## Inputs

- `object` (`object_ref`): The resting object to hold still.

## Applicability

Requires hand_empty(hand=left); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=left)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `steadied(object=$object)` — The left gripper pinches the object while it still rests on its support. GT: left_gripper_state, object_pose.
- `holding(hand=left, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `steadied(object=$object)` (all paths)
- `holding(hand=left, object=$object)` (all paths)

## May invalidate

`arm_stowed(left)`, `hand_empty(left)`

## Policy paths (first match on the bound nouns)

### `left_rim_pinch` — when object.location in ['support', 'floor', 'container']

1. `policy_077($object)`
- Only an object standing in the open (not behind an appliance or cabinet door).

## Relations

- Next step: `stir` (`skill_038`) (then) — the braced container is stirred
- Next step: `release` (`skill_021`) (enables) — bracing is finished
- Is a fallback for: `stir` (`skill_038`) (recover) — the container slides while stirring
- Alternative: `handover` (`skill_022`) — the left hand should hold an object that stays on its support

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_035`.
