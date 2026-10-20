---
name: present-object
description: Hold the carried object in front of the body at 0.9-1.4 m height, inside the head camera view.
---

# Present a held object (`skill_016`)

`present(object: object_ref)`

Hold the carried object in front of the body at 0.9-1.4 m height, inside the head camera view.

## When to use

A held object must be shown to the head camera or a person.

## Not to be confused with

- `lift`: lift only changes the height; present holds the object in front of the head.

## Inputs

- `object` (`object_ref`): The right-held object to show.

## Applicability

Requires holding(hand=right, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `presenting(object=$object)` — The right-held object is in front of the body at 0.9-1.4 m height and in the head camera view. GT: object_pose, base_pose, head_fk.
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `presenting(object=$object)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## May invalidate

`reachable(*)`

## Policy paths (first match on the bound nouns)

### `front_of_head` — when always (default path)

1. `policy_072($object)`

## Relations

- Next step: `place` (`skill_018`) (enables) — the object is put away after showing it
- Next step: `handover` (`skill_022`) (enables) — the object is passed to the left hand
- Alternative: `lift` (`skill_023`) — only the height of the load matters

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_024`.
