---
name: stand-torso
description: "Raise the torso lift to its top travel height."
---

# Stand up to full height (`skill_006`)

`stand()`

Raise the torso lift to its top travel height.

## When to use

After a crouch, before driving or reaching high.

## Not to be confused with

- `lift`: lift raises a held object, stand raises the body.
- `straighten`: straighten undoes a waist bend; stand raises the torso.

## Inputs

- none

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `torso_raised()` — Torso lift within 3 cm of its highest position (travel height). GT: torso_joint.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `torso_raised()` (all paths)

## May invalidate

`torso_lowered()`, `reachable(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `highest` — when always (default path)

1. `policy_006()`

## Relations

- Previous step: `crouch` (`skill_005`) (then) — low work is done
- Next step: `navigate` (`skill_001`) (then) — the robot drives after low work
- Alternative: `reset` (`skill_010`) — the arm and waist must also be restored

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_014`.
