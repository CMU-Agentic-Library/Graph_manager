---
name: tuck-arm
description: Fold an empty arm to its travel posture along a collision-checked path.
---

# Tuck an arm (`skill_009`)

`tuck(hand: hand)`

Fold an empty arm to its travel posture along a collision-checked path.

## When to use

Before driving through a narrow passage or after a hand action left the arm out.

## Not to be confused with

- `reset`: reset also restores torso, waist and head; tuck only folds the arm.

## Inputs

- `hand` (`hand`, default 'right'): Which arm to fold.

## Applicability

Requires hand_empty(hand=$hand).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=$hand)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `arm_stowed(hand=$hand)` — The arm is folded at its travel posture. GT: arm_joints.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `arm_stowed(hand=$hand)` (all paths)

## May invalidate

`reachable(*)`, `pointing_at(*)`

## Policy paths (first match on the bound nouns)

### `left` — when args.hand == 'left'

1. `policy_091()`

### `right` — when always (default path)

1. `policy_003()`

## Relations

- Previous step: `point` (`skill_015`) (enables) — the gesture is finished
- Previous step: `place` (`skill_018`) (enables) — the hand is empty and the robot drives next
- Previous step: `release` (`skill_021`) (enables) — the arm is folded after letting go
- Previous step: `press` (`skill_042`) (enables) — the hand is free again
- Previous step: `restore` (`skill_053`) (enables) — the robot drives on
- Previous step: `swap` (`skill_054`) (enables) — the robot drives on
- Previous step: `hide` (`skill_070`) (enables) — the robot leaves
- Next step: `navigate` (`skill_001`) (then) — the robot drives next
- Fallback on failure: `retreat` (`skill_004`) (recover) — the fold collides with furniture
- Is a fallback for: `navigate` (`skill_001`) (recover) — navigation fails because the empty arm cannot fold

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_017`.
