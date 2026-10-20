---
name: point-target
description: "Point the closed right fingers at a target (finger axis within 8 deg) to indicate it."
---

# Point at a target (`skill_015`)

`point(target: entity_ref)`

Point the closed right fingers at a target (finger axis within 8 deg) to indicate it.

## When to use

A person must be shown an object or place without touching it.

## Not to be confused with

- `touch`: point does not make contact.

## Inputs

- `target` (`entity_ref`): What to indicate.

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `pointing_at(target=$target)` — The right finger axis points at the target within 8 deg. GT: arm_fk, scene_annotation.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `pointing_at(target=$target)` (all paths)
- `hand_empty(hand=right)` (all paths)

## May invalidate

`arm_stowed(right)`, `reachable(*)`

## Policy paths (first match on the bound nouns)

### `front` — when target.bearing_abs_deg <= 60

1. `policy_041()`
2. `policy_101($target) as aim`
3. `policy_038(#aim.position, #aim.rotation, position_tolerance=0.04, rotation_tolerance=0.2)`

### `turn_and_point` — when always (default path)

1. `policy_071($target)`

## Relations

- Previous step: `face` (`skill_003`) (then) — the target must be indicated
- Previous step: `wave` (`skill_060`) (enables) — the robot then indicates something
- Next step: `tuck` (`skill_009`) (enables) — the gesture is finished
- Alternative: `look` (`skill_011`) — a gaze is enough to indicate the target
- Alternative: `touch` (`skill_065`) — contact is not allowed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_023`.
