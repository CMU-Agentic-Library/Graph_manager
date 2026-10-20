---
name: crouch-torso
description: Lower the torso lift to its bottom (or a requested height) for floor and low-shelf work.
---

# Crouch the torso (`skill_005`)

`crouch(height_m: number?)`

Lower the torso lift to its bottom (or a requested height) for floor and low-shelf work.

## When to use

The next target is low (floor, low shelf) or the head must look under something.

## Not to be confused with

- `bend`: bend pitches the waist forward; crouch lowers the torso vertically.

## Inputs

- `height_m` (`number`, optional): Optional torso joint target in [-0.54, 0]; omit for the lowest.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `not torso_raised()` — Torso lift within 3 cm of its highest position (travel height). GT: torso_joint.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `not torso_raised()` (all paths)
- `torso_at(height_m=$height_m)` (path to_height)
- `torso_lowered()` (path lowest)

## May invalidate

`torso_raised()`, `torso_lowered()`, `torso_at(*)`, `reachable(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `to_height` — when args.height_m

1. `policy_004($height_m)`
- extra postcondition `torso_at(height_m=$height_m)`

### `lowest` — when always (default path)

1. `policy_005()`
- extra postcondition `torso_lowered()`

## Relations

- Next step: `pick` (`skill_017`) (then) — the object is on the floor or a low shelf
- Next step: `stand` (`skill_006`) (then) — low work is done
- Is a fallback for: `pick` (`skill_017`) (recover) — the object is on the floor or a low shelf

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_013`.
