---
name: sidestep-base
description: "Move the base sideways by a signed distance (left positive) without turning, also while carrying a load; aligns the arm with a target that is a little to the side."
---

# Sidestep the base (`skill_055`)

`sidestep(distance_m: number)`

Move the base sideways by a signed distance (left positive) without turning, also while carrying a load; aligns the arm with a target that is a little to the side.

## When to use

The robot must shift sideways a few centimetres without turning (align with a target).

## Not to be confused with

- `retreat`: retreat moves straight back; sidestep moves sideways.
- `face`: face turns in place; sidestep keeps the heading.

## Inputs

- `distance_m` (`number`): Lateral displacement in metres (left > 0).

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `sidestepped(distance_m=$distance_m)` — Base moved sideways by the signed distance (left > 0) within 3 cm, heading unchanged within 3 deg. GT: base_pose (before/after).

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `sidestepped(distance_m=$distance_m)` (all paths)

## May invalidate

`base_near(*)`, `reachable(*)`, `facing(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `empty_tucked` — when not robot.right_held and not robot.left_held and robot.right_arm_stowed

1. `policy_037(0.0, $distance_m)`

### `loaded` — when always (default path)

1. `policy_114($distance_m)`

## Relations

- Next step: `approach` (`skill_002`) (then) — the target is now in front of the arm
- Alternative: `navigate` (`skill_001`) — a larger move is needed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_063`.
