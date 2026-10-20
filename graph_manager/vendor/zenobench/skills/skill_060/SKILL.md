---
name: wave-hand
description: Raise the empty right hand at head height and swing it (greeting / attention gesture).
---

# Wave the hand (`skill_060`)

`wave()`

Raise the empty right hand at head height and swing it (greeting / attention gesture).

## When to use

Greeting or getting attention.

## Not to be confused with

- `point`: point indicates a target; wave is a greeting.

## Inputs

- none

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `waved()` — The right hand performed a measured wave (>= 2 lateral swings at head height). GT: robot_memory (TCP swing samples).
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `waved()` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `raised_swing` — when always (default path)

1. `policy_104()`

## Relations

- Next step: `point` (`skill_015`) (enables) — the robot then indicates something
- Alternative: `nod` (`skill_061`) — an acknowledgement without the arm

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_068`.
