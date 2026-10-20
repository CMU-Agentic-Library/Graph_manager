---
name: touch-object
description: Bring the closed fingertips onto an object's top and back off without moving it (probe / indicate by contact).
---

# Touch an object (`skill_065`)

`touch(object: object_ref)`

Bring the closed fingertips onto an object's top and back off without moving it (probe / indicate by contact).

## When to use

An object must be touched lightly (tap, confirm contact) without moving it.

## Not to be confused with

- `push`: push moves the object; touch must not.
- `press`: press actuates a button.

## Inputs

- `object` (`object_ref`): The object to touch.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `touched(object=$object)` — A measured fingertip contact with the object's top during the Contract; it moved < 1.5 cm. GT: event_log (fingertip contact), object_pose (before/after).
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `touched(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `fingertip_top` — when always (default path)

1. `policy_107($object)`

## Relations

- Next step: `pick` (`skill_017`) (enables) — the touched object is then grasped
- Alternative: `point` (`skill_015`) — contact is not allowed
- Alternative: `knock` (`skill_066`) — an object, not a door, is to be tapped

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_073`.
