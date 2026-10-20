---
name: nod-head
description: Pitch the head down and up twice (acknowledgement gesture).
---

# Nod the head (`skill_061`)

`nod()`

Pitch the head down and up twice (acknowledgement gesture).

## When to use

Acknowledging an instruction.

## Not to be confused with

- `wave`: wave uses the arm; nod uses the head.

## Inputs

- none

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `nodded()` — The head performed a measured nod (>= 2 pitch cycles of >= 0.2 rad). GT: robot_memory (head joint samples).

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `nodded()` (all paths)

## May invalidate

`in_view(*)`

## Policy paths (first match on the bound nouns)

### `pitch_cycles` — when always (default path)

1. `policy_105()`

## Relations

- Next step: `look` (`skill_011`) (then) — the robot looks back at a target
- Alternative: `wave` (`skill_060`) — a bigger gesture is needed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_069`.
