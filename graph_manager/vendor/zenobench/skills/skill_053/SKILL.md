---
name: restore-object
description: "Return an object to the support it occupied at the start of the episode."
---

# Restore an object to its place (`skill_053`)

`restore(object: object_ref)`

Return an object to the support it occupied at the start of the episode.

## When to use

An object must return to where it was at the start.

## Not to be confused with

- `fetch`: restore's destination is the object's initial support.

## Inputs

- `object` (`object_ref`): The displaced object.

## Applicability

Requires hand_empty(hand=right); not at_initial_place(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `not at_initial_place(object=$object)` — Object is back on the support it occupied when the episode started. GT: object_pose, initial_scene_annotation.

## Postconditions (verified on live GT state)

- `at_initial_place(object=$object)` — Object is back on the support it occupied when the episode started. GT: object_pose, initial_scene_annotation.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `at_initial_place(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `dispatch_pick_place` — when object.initial_support

1. `policy_092($object)`
2. `policy_061($object)`
3. `policy_092(@object.initial_support)`
4. `policy_015($object, @object.initial_support)`

## Relations

- Next step: `tuck` (`skill_009`) (enables) — the robot drives on
- Alternative: `fetch` (`skill_047`) — a different destination is wanted

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_061`.
