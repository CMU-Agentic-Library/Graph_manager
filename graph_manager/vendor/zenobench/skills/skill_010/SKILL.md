---
name: reset-posture
description: Return to the home posture: fingers open, arm folded, torso up, waist straight, by a collision-checked joint-space move. Used to recover from an unknown arm state.
---

# Reset the posture (`skill_010`)

`reset()`

Return to the home posture: fingers open, arm folded, torso up, waist straight, by a collision-checked joint-space move. Used to recover from an unknown arm state.

## When to use

Start or end of a task, or after a failure, to return to a known posture.

## Not to be confused with

- `tuck`: tuck only folds one arm; reset also restores torso and waist.

## Inputs

- none

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `arm_stowed(hand=right)` — The arm is folded at its travel posture. GT: arm_joints.
- `torso_raised()` — Torso lift within 3 cm of its highest position (travel height). GT: torso_joint.
- `waist_straight()` — Waist pitch within 0.05 rad of upright. GT: waist_joint.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `arm_stowed(hand=right)` (all paths)
- `torso_raised()` (all paths)
- `waist_straight()` (all paths)

## May invalidate

`torso_lowered()`, `waist_bent(*)`, `reachable(*)`, `pointing_at(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `joint_home` — when always (default path)

1. `policy_040()`
2. `policy_003()`
3. `policy_095() as home`
4. `policy_039(#home.target)`

## Relations

- Next step: `navigate` (`skill_001`) (then) — after a failed manipulation, before driving on
- Alternative: `stand` (`skill_006`) — the arm and waist must also be restored
- Alternative: `straighten` (`skill_008`) — the arm and torso must also be restored

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_018`.
