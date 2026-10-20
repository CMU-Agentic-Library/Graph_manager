---
name: bend-waist
description: Pitch the waist forward to extend the reach over a deep surface.
---

# Bend the waist (`skill_007`)

`bend(pitch_rad: positive_number?)`

Pitch the waist forward to extend the reach over a deep surface.

## When to use

A target is just beyond arm reach over a counter and leaning forward helps.

## Not to be confused with

- `crouch`: crouch lowers the torso; bend tilts the waist.

## Inputs

- `pitch_rad` (`positive_number`, optional): Forward pitch in rad (max 0.69); omit for the maximum.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `waist_bent(min_pitch_rad=0.2)` — Waist pitched forward by at least the given angle. GT: waist_joint.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `waist_bent(min_pitch_rad=0.2)` (all paths)

## May invalidate

`waist_straight()`, `reachable(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `to_pitch` — when args.pitch_rad

1. `policy_007($pitch_rad)`

### `full` — when always (default path)

1. `policy_008()`

## Relations

- Next step: `straighten` (`skill_008`) (then) — the reach is done
- Next step: `approach` (`skill_002`) (then) — the target was just out of reach
- Is a fallback for: `approach` (`skill_002`) (recover) — the target is just beyond the arm envelope

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_015`.
