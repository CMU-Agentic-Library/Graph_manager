---
name: roll-object
description: "Roll a lying constant-radius cylinder (rolling pin, can on its side) along its support by pressing on its top; the object must rotate, not slide. A bottle with a neck rolls in an arc around the neck and is not a valid noun."
---

# Roll a cylinder (`skill_034`)

`roll(object: object_ref, distance_m: positive_number)`

Roll a lying constant-radius cylinder (rolling pin, can on its side) along its support by pressing on its top; the object must rotate, not slide. A bottle with a neck rolls in an arc around the neck and is not a valid noun.

## When to use

A lying cylinder must move along the support by rotating.

## Not to be confused with

- `push`: push slides the object; roll makes it rotate.

## Inputs

- `object` (`object_ref`): A lying cylinder.
- `distance_m` (`positive_number`, default 0.1): Requested travel.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object); lying(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `lying(object=$object)` — Object on its side: longest axis within 60 deg of horizontal and vertical extent <= 60 % of its length. GT: object_pose, asset_annotation.

## Postconditions (verified on live GT state)

- `object_rolled(object=$object)` — Object rotated at least 45 deg about a horizontal axis while staying on its side. GT: object_pose (before/after).

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `object_rolled(object=$object)` (all paths)

## May invalidate

`at_initial_place($object)`, `grasp_clearance($object)`

## Policy paths (first match on the bound nouns)

### `push_above_axis` — when always (default path)

1. `policy_081($object, $distance_m)`

## Relations

- Previous step: `tip` (`skill_035`) (enables) — the lying cylinder is rolled
- Next step: `pick` (`skill_017`) (then) — the rolled object is then grasped
- Alternative: `push` (`skill_029`) — sliding is acceptable

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_042`.
