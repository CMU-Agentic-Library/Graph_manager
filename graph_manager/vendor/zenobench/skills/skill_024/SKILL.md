---
name: lower-object
description: Move the held object down until its bottom is at most the given height (e.g. under a low shelf clearance).
---

# Lower a held object (`skill_024`)

`lower(object: object_ref, height_m: positive_number)`

Move the held object down until its bottom is at most the given height (e.g. under a low shelf clearance).

## When to use

A held object must be brought down to a height without releasing it.

## Not to be confused with

- `place`: lower keeps holding the object.

## Inputs

- `object` (`object_ref`): The held object.
- `height_m` (`positive_number`): Maximum world height of the object's bottom.

## Applicability

Requires holding(hand=right, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `held_below(object=$object, height_m=$height_m)` — Right-held object's bottom at or below the given world height (2 cm tolerance). GT: object_pose, gripper_state.
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `held_below(object=$object, height_m=$height_m)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## May invalidate

`held_above($object,*)`

## Policy paths (first match on the bound nouns)

### `descend` — when always (default path)

1. `policy_093($object, $height_m)`

## Relations

- Next step: `place` (`skill_018`) (enables) — the object goes onto a low shelf or into the fridge
- Alternative: `lift` (`skill_023`) — opposite direction

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_032`.
