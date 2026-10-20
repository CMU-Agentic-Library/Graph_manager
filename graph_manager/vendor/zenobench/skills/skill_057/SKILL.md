---
name: identify-object
description: "Look at an object and report its category and tags (asset annotation) once it is in the head camera view."
---

# Identify an object (`skill_057`)

`identify(object: object_ref)`

Look at an object and report its category and tags (asset annotation) once it is in the head camera view.

## When to use

The category or identity of a visible object must be confirmed.

## Not to be confused with

- `look`: look only aims the camera.
- `measure`: measure reports dimensions.

## Inputs

- `object` (`object_ref`): The object to identify.

## Outputs

- `category` (`tag`): Asset category.
- `tags` (`object_list`): Annotated tags.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `identified(object=$object)` — The robot recorded the object's category while it was in the head camera view. GT: robot_memory, asset_annotation.
- `in_view(target=$object)` — Target point inside the head camera frustum, within 5 m, line of sight not blocked by furniture boxes. GT: base_pose, head_joints, head_fk, collision_model.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `identified(object=$object)` (all paths)
- `in_view(target=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `look_and_label` — when always (default path)

1. `policy_110($object)`

## Relations

- Next step: `sort` (`skill_049`) (then) — the category decides the destination
- Fallback on failure: `navigate` (`skill_001`) (recover) — the object is not visible from here
- Alternative: `measure` (`skill_058`) — the size, not the category, is needed

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_065`.
