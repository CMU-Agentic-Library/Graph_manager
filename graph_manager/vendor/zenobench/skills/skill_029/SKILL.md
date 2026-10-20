---
name: push-object
description: "Slide an object along its support in a direction with closed fingers: from behind when there is room, or by pressing on its top and dragging when it stands against a wall or closed edge."
---

# Push an object (`skill_029`)

`push(object: object_ref, direction_xy: unit_vec2, distance_m: positive_number)`

Slide an object along its support in a direction with closed fingers: from behind when there is room, or by pressing on its top and dragging when it stands against a wall or closed edge.

## When to use

An object must slide along its support without grasping it.

## Not to be confused with

- `pull`: pull drags toward the base to make an object reachable.
- `expose`: expose pushes until a graspable overhang exists.
- `separate`: separate pushes away from the nearest neighbour.
- `center`: center pushes away from the support edges.
- `roll`: roll makes a cylinder rotate instead of slide.
- `tip`: tip pushes high so the object falls over.
- `sweep`: sweep gathers several objects.

## Inputs

- `object` (`object_ref`): The object to slide.
- `direction_xy` (`unit_vec2`): World horizontal direction.
- `distance_m` (`positive_number`): Requested travel.

## Outputs

- `moved_m` (`number`): Measured displacement along the direction.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `object_moved(object=$object, direction_xy=$direction_xy, distance_m=$distance_m)` — Object displaced along the direction by at least half the requested distance. GT: object_pose (before/after).

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `object_moved(object=$object, direction_xy=$direction_xy, distance_m=$distance_m)` (all paths)

## May invalidate

`edge_overhang($object)`, `grasp_clearance($object)`, `away_from_edge($object,*)`, `at_initial_place($object)`

## Policy paths (first match on the bound nouns)

### `drag_from_top` — when object.near_closed_edge

1. `policy_041()`
2. `policy_044($object, @object.support, $direction_xy, $distance_m)`

### `thin_auto` — when object.flat

1. `policy_026($object, @object.support, $direction_xy, $distance_m)`
- The dispatcher chooses push or drag for thin items.

### `from_behind` — when always (default path)

1. `policy_041()`
2. `policy_043($object, @object.support, $direction_xy, $distance_m)`

## Relations

- Next step: `pick` (`skill_017`) (then) — the object was pushed into a graspable spot
- Alternative: `pull` (`skill_030`) — the object should come toward the robot
- Alternative: `center` (`skill_033`) — a specific direction is wanted
- Alternative: `roll` (`skill_034`) — sliding is acceptable
- Alternative: `sweep` (`skill_067`) — only one object has to move

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_037`.
