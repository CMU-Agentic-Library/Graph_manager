---
name: flip-object
description: Turn a flat object upside down where it lies: slide it to an edge, pinch the overhang, lift, roll the hand 180 deg, lay it back and release.
---

# Flip a flat object over (`skill_028`)

`flip(object: object_ref)`

Turn a flat object upside down where it lies: slide it to an edge, pinch the overhang, lift, roll the hand 180 deg, lay it back and release.

## When to use

A flat object must be turned upside down.

## Not to be confused with

- `rotate`: rotate turns about the vertical axis; flip turns the object upside down.

## Inputs

- `object` (`object_ref`): A flat object (book, plate, notebook) on a support.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `flipped(object=$object)` — Object's local z axis now points opposite to its direction at the start (dot <= -0.7). GT: object_pose (before/after).
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `flipped(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `edge_roll` — when object.flat

1. `policy_045($object)`
2. `policy_013($object)`
3. `policy_078($object)`

## Relations

- Previous step: `expose` (`skill_031`) (then) — turn the object over
- Next step: `center` (`skill_033`) (enables) — the object is left overhanging the edge
- Fallback on failure: `center` (`skill_033`) (recover) — the flipped object landed too close to the edge

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_036`.
