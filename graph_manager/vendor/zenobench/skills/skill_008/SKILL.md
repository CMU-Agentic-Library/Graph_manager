---
name: straighten-waist
description: "Return the waist pitch to upright."
---

# Straighten the waist (`skill_008`)

`straighten()`

Return the waist pitch to upright.

## When to use

After a bend, before driving or carrying.

## Not to be confused with

- `stand`: stand raises the torso; straighten undoes a waist bend.

## Inputs

- none

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `waist_straight()` — Waist pitch within 0.05 rad of upright. GT: waist_joint.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `waist_straight()` (all paths)

## May invalidate

`waist_bent(*)`, `reachable(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `upright` — when always (default path)

1. `policy_009()`

## Relations

- Previous step: `bend` (`skill_007`) (then) — the reach is done
- Next step: `navigate` (`skill_001`) (then) — the robot drives after a bent reach
- Alternative: `reset` (`skill_010`) — the arm and torso must also be restored

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_016`.
