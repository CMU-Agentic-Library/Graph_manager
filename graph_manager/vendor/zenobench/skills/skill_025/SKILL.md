---
name: rotate-object
description: Turn the held object about the vertical axis by the requested angle (e.g. align a book's spine).
---

# Rotate a held object (`skill_025`)

`rotate(object: object_ref, degrees: number)`

Turn the held object about the vertical axis by the requested angle (e.g. align a book's spine).

## When to use

A held object must turn about the vertical axis (align a handle or label).

## Not to be confused with

- `flip`: flip turns an object upside down; rotate keeps it level.

## Inputs

- `object` (`object_ref`): The held object.
- `degrees` (`number`): Yaw change in degrees (positive = counter-clockwise).

## Applicability

Requires holding(hand=right, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `yaw_rotated(object=$object, degrees=$degrees)` — Object yaw changed by the requested angle within 10 deg. GT: object_pose (before/after).
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `yaw_rotated(object=$object, degrees=$degrees)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `wrist_yaw` — when always (default path)

1. `policy_075($object, $degrees)`

## Relations

- Next step: `place` (`skill_018`) (enables) — the object is set down in the new orientation
- Alternative: `regrasp` (`skill_026`) — the grasp, not the yaw, must change
- Alternative: `shake` (`skill_062`) — the orientation, not the contents, matters
- Alternative: `square` (`skill_064`) — the object is already in the hand

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_033`.
