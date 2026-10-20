---
name: lift-object
description: "Raise the held object until its bottom is at least the given world height (e.g. above a bin rim or a furniture edge before carrying)."
---

# Lift a held object (`skill_023`)

`lift(object: object_ref, height_m: positive_number)`

Raise the held object until its bottom is at least the given world height (e.g. above a bin rim or a furniture edge before carrying).

## When to use

A held object must be raised to a height (clear an obstacle, show it).

## Not to be confused with

- `stand`: stand moves the torso, not the held object.
- `lower`: opposite direction.
- `pick`: lift raises an object already held.

## Inputs

- `object` (`object_ref`): The held object.
- `height_m` (`positive_number`, default 0.55): Minimum world height of the object's bottom.

## Applicability

Requires holding(hand=right, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `held_above(object=$object, height_m=$height_m)` — Right-held object's bottom at or above the given world height (2 cm tolerance). GT: object_pose, gripper_state.
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `held_above(object=$object, height_m=$height_m)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## May invalidate

`held_below($object,*)`

## Policy paths (first match on the bound nouns)

### `raise` — when always (default path)

1. `policy_034($height_m)`

## Relations

- Previous step: `pick` (`skill_017`) (enables) — the object must clear a high rim while carried
- Next step: `navigate` (`skill_001`) (then) — the object is carried over furniture
- Next step: `drop` (`skill_019`) (enables) — the object is released over a tall container
- Is a fallback for: `navigate` (`skill_001`) (recover) — a carried object hangs too low for the doorway clearance
- Alternative: `present` (`skill_016`) — only the height of the load matters
- Alternative: `lower` (`skill_024`) — opposite direction
- Alternative: `hover` (`skill_063`) — only a height matters

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_031`.
