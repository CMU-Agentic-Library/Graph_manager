---
name: drop-object
description: Hold the object 5 cm above a container's opening, centred, and let go; the object falls in.
---

# Drop an object into a container (`skill_019`)

`drop(object: object_ref, container: container_ref)`

Hold the object 5 cm above a container's opening, centred, and let go; the object falls in.

## When to use

A held object must go into an open container from above without a precise pose.

## Not to be confused with

- `place`: place lowers the object onto the container floor before opening.

## Inputs

- `object` (`object_ref`): The held object.
- `container` (`container_ref`): The open container.

## Applicability

Requires holding(hand=right, object=$object); base_near(place=$container); uncovered(container=$container).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$container)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `uncovered(container=$container)` — No lid rests on the container rim. GT: object_pose, container_profile, asset_tags.

## Postconditions (verified on live GT state)

- `inside(object=$object, container=$container)` — Object centre inside the container's wall profile, between its floor and 3 cm above the rim. GT: object_pose, container_profile.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `inside(object=$object, container=$container)` (all paths)
- `hand_empty(hand=right)` (all paths)

## May invalidate

`holding(right,$object)`

## Policy paths (first match on the bound nouns)

### `above_opening` — when always (default path)

1. `policy_073($object, $container)`

## Relations

- Previous step: `lift` (`skill_023`) (enables) — the object is released over a tall container
- Previous step: `hover` (`skill_063`) (enables) — the object is released into the container under it
- Next step: `pick` (`skill_017`) (enables) — more items go into the same container
- Is a fallback for: `place` (`skill_018`) (substitute) — a deep container leaves no room to lower the hand inside
- Alternative: `place` (`skill_018`) — a gentle release inside is needed
- Alternative: `release` (`skill_021`) — the object should fall into a container

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_027`.
