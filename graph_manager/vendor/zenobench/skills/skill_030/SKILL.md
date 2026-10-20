---
name: pull-object
description: "Drag an object toward the robot with the pads pressed on its top until it is within reach (e.g. from the back of a deep counter); if the pads slide over a round or slippery top, the fingers hook the far side and push it toward the robot."
---

# Pull an object closer (`skill_030`)

`pull(object: object_ref, distance_m: positive_number)`

Drag an object toward the robot with the pads pressed on its top until it is within reach (e.g. from the back of a deep counter); if the pads slide over a round or slippery top, the fingers hook the far side and push it toward the robot.

## When to use

An object is too far back on a deep support to grasp and must come closer.

## Not to be confused with

- `push`: push moves the object away from the robot or sideways.

## Inputs

- `object` (`object_ref`): The object to drag.
- `distance_m` (`positive_number`, default 0.15): Requested travel toward the base.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `moved_toward_base(object=$object, distance_m=$distance_m)` — Object's horizontal distance to the base decreased by at least half the requested distance. GT: object_pose (before/after), base_pose.
- `reachable(target=$object)` — From the current base pose the right TCP has a collision-free IK solution 10 cm above the target (handle pre-grasp for doors, 8 cm in front of a button). GT: base_pose, arm_ik, collision_model, object_pose, grasp_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `moved_toward_base(object=$object, distance_m=$distance_m)` (all paths)
- `reachable(target=$object)` (all paths)

## May invalidate

`grasp_clearance($object)`, `at_initial_place($object)`

## Policy paths (first match on the bound nouns)

### `top_drag` — when always (default path)

1. `policy_041()`
2. `policy_079($object, $distance_m)`

## Relations

- Next step: `pick` (`skill_017`) (then) — the object is now close enough to grasp
- Is a fallback for: `approach` (`skill_002`) (substitute) — the object sits too deep on its support
- Is a fallback for: `pick` (`skill_017`) (recover) — the object sits too deep to reach
- Alternative: `push` (`skill_029`) — the object should come toward the robot

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_038`.
