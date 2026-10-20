---
name: separate-object
description: "Push an object straight away from its closest neighbour until there is room for a finger (>= 3.5 cm gap) without leaving the support."
---

# Separate an object from its neighbour (`skill_032`)

`separate(object: object_ref)`

Push an object straight away from its closest neighbour until there is room for a finger (>= 3.5 cm gap) without leaving the support.

## When to use

Two objects are too close for the fingers to fit beside one of them.

## Not to be confused with

- `push`: separate pushes until a finger fits beside the object.

## Inputs

- `object` (`object_ref`): The crowded object.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object); not grasp_clearance(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `not grasp_clearance(object=$object)` — Some annotated pinch of the object has both finger slots (2.8 x 1.2 cm, at the pre-grasp opening) free of neighbours; objects without a pinch need 3.5 cm of free footprint gap. GT: object_pose, asset_annotation.

## Postconditions (verified on live GT state)

- `grasp_clearance(object=$object)` — Some annotated pinch of the object has both finger slots (2.8 x 1.2 cm, at the pre-grasp opening) free of neighbours; objects without a pinch need 3.5 cm of free footprint gap. GT: object_pose, asset_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `grasp_clearance(object=$object)` (all paths)

## May invalidate

`at_initial_place($object)`

## Policy paths (first match on the bound nouns)

### `push_apart` — when always (default path)

1. `policy_080($object)`

## Relations

- Next step: `pick` (`skill_017`) (enables) — grasp the freed object
- Is a fallback for: `pick` (`skill_017`) (repair) — fingers have no room beside the object (grasp_clearance false)

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_040`.
