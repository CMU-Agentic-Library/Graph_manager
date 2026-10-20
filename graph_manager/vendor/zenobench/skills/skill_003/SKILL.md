---
name: face-target
description: Rotate the base in place until it faces the target (heading error <= 20 deg).
---

# Face a target (`skill_003`)

`face(target: entity_ref)`

Rotate the base in place until it faces the target (heading error <= 20 deg).

## When to use

The target is beside or behind the robot and only the heading must change.

## Not to be confused with

- `look`: look moves the head only; face moves the whole base.

## Inputs

- `target` (`entity_ref`): What to face.

## Outputs

- `base_yaw_deg` (`number`): Measured heading after the turn.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `facing(target=$target)` — Base heading within 20 deg of the target bearing. GT: base_pose, scene_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `facing(target=$target)` (all paths)

## May invalidate

`reachable(*)`, `in_view(*)`, `pointing_at(*)`

## Policy paths (first match on the bound nouns)

### `rotate_empty` — when not robot.right_held and not robot.left_held and robot.right_arm_stowed

1. `policy_099($target) as heading`
2. `policy_036(#heading.delta_yaw_deg)`
- Tucked and empty: the measured in-place rotation primitive.

### `rotate_loaded` — when always (default path)

1. `policy_066($target)`
- With a load or unfolded arm: slower turn with grasp checks.

## Relations

- Next step: `look` (`skill_011`) (then) — the target must be observed
- Next step: `point` (`skill_015`) (then) — the target must be indicated
- Alternative: `navigate` (`skill_001`) — turning in place is blocked by furniture

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.

- turning in place would hit furniture

Paired Contract: `contract_011`.
