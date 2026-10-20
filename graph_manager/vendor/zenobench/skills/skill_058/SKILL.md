---
name: measure-object
description: Look at an object and report its current axis-aligned size.
---

# Measure an object (`skill_058`)

`measure(object: object_ref)`

Look at an object and report its current axis-aligned size.

## When to use

The size or distance of an object must be known before choosing a grasp or place.

## Not to be confused with

- `identify`: identify returns the category, measure the size and distance.

## Inputs

- `object` (`object_ref`): The object to measure.

## Outputs

- `size_m` (`xy`): World-frame size [dx, dy, dz] in metres.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `measured(object=$object)` — The robot recorded the object's size from a view with the object in the head camera. GT: robot_memory, asset_annotation, object_pose.
- `in_view(target=$object)` — Target point inside the head camera frustum, within 5 m, line of sight not blocked by furniture boxes. GT: base_pose, head_joints, head_fk, collision_model.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `measured(object=$object)` (all paths)
- `in_view(target=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `look_and_size` — when always (default path)

1. `policy_111($object)`

## Relations

- Next step: `pick` (`skill_017`) (then) — the size decides the grasp
- Alternative: `identify` (`skill_057`) — the category is needed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_066`.
