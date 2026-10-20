---
name: retreat-obstacle
description: "Back the base straight away from a piece of furniture, appliance or object until it is at least the given distance away; a held load stays held."
---

# Retreat from an obstacle (`skill_004`)

`retreat(obstacle: place_ref, distance_m: positive_number)`

Back the base straight away from a piece of furniture, appliance or object until it is at least the given distance away; a held load stays held.

## When to use

The base is too close to open a door, turn, or start a path.

## Not to be confused with

- `navigate`: retreat has no destination; it only increases clearance.

## Inputs

- `obstacle` (`place_ref`): What to back away from.
- `distance_m` (`positive_number`, default 0.4): Required clearance from the obstacle footprint.

## Outputs

- `moved_m` (`number`): Measured base displacement.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `base_clear_of(place=$obstacle, distance_m=$distance_m)` — Base centre at least the given distance from the place's footprint. GT: base_pose, scene_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `base_clear_of(place=$obstacle, distance_m=$distance_m)` (all paths)

## May invalidate

`base_near(*)`, `reachable(*)`, `facing(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `microwave_door_sweep` — when obstacle.instance == 'kitchen_microwave'

1. `policy_030($obstacle)`
- The microwave's measured hinge-clearance pose (also when loaded).

### `bimanual_or_left_load` — when robot.left_held

1. `policy_067($obstacle, $distance_m)`

### `loaded` — when robot.right_held

1. `policy_035($distance_m)`
- Straight reverse with the right-hand load.

### `empty` — when always (default path)

1. `policy_100($obstacle, $distance_m) as plan`
2. `policy_037(#plan.forward_m)`

## Relations

- Next step: `navigate` (`skill_001`) (then) — the robot must leave after backing out
- Next step: `open` (`skill_040`) (then) — a door's swing needs room in front of the robot
- Is a fallback for: `navigate` (`skill_001`) (recover) — navigation fails because the base or load is wedged against furniture
- Is a fallback for: `tuck` (`skill_009`) (recover) — the fold collides with furniture
- Is a fallback for: `open` (`skill_040`) (recover) — the door swing hits the base
- Is a fallback for: `close` (`skill_041`) (recover) — the door swing hits the base

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.

- the path behind the base is blocked

Paired Contract: `contract_012`.
