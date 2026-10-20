---
name: handover-object
description: Transfer a right-held object into the left gripper and open the right gripper.
---

# Hand an object over to the left hand (`skill_022`)

`handover(object: object_ref)`

Transfer a right-held object into the left gripper and open the right gripper.

## When to use

The right hand must be freed while the object stays held (by the left hand).

## Not to be confused with

- `release`: release lets the object go; handover keeps it held by the left hand.

## Inputs

- `object` (`object_ref`): The right-held object.

## Applicability

Requires holding(hand=right, object=$object); hand_empty(hand=left).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `hand_empty(hand=left)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `holding(hand=left, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `holding(hand=left, object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## May invalidate

`holding(right,$object)`

## Policy paths (first match on the bound nouns)

### `right_to_left` — when always (default path)

1. `policy_059($object)`

## Relations

- Previous step: `present` (`skill_016`) (enables) — the object is passed to the left hand
- Next step: `open` (`skill_040`) (enables) — the right hand must open a door while the left carries the load
- Next step: `pick` (`skill_017`) (enables) — a second object is picked with the free right hand
- Is a fallback for: `open` (`skill_040`) (repair) — the right hand still holds a load
- Alternative: `brace` (`skill_027`) — the left hand should hold an object that stays on its support

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_030`.
