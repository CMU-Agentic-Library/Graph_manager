---
name: center-object
description: "Push an object back from the support edges until every edge margin is at least the requested value (secures an item left overhanging)."
---

# Center an object on its support (`skill_033`)

`center(object: object_ref, margin_m: positive_number)`

Push an object back from the support edges until every edge margin is at least the requested value (secures an item left overhanging).

## When to use

An object near a support edge must be moved inward so it cannot fall.

## Not to be confused with

- `push`: center moves the object away from the nearest edge by a margin.

## Inputs

- `object` (`object_ref`): The object near an edge.
- `margin_m` (`positive_number`, default 0.06): Required margin to every edge.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `away_from_edge(object=$object, margin_m=$margin_m)` — Object footprint at least the margin inside every edge of its support. GT: object_pose, support_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `away_from_edge(object=$object, margin_m=$margin_m)` (all paths)

## May invalidate

`edge_overhang($object)`

## Policy paths (first match on the bound nouns)

### `push_inward` — when always (default path)

1. `policy_083($object, $margin_m)`

## Relations

- Previous step: `flip` (`skill_028`) (enables) — the object is left overhanging the edge
- Next step: `pick` (`skill_017`) (then) — the secured object is grasped later
- Is a fallback for: `flip` (`skill_028`) (recover) — the flipped object landed too close to the edge
- Alternative: `push` (`skill_029`) — a specific direction is wanted

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_041`.
