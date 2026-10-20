---
name: shake-object
description: "Oscillate the held object sideways three times (settle or loosen contents) while keeping the grasp."
---

# Shake a held object (`skill_062`)

`shake(object: object_ref)`

Oscillate the held object sideways three times (settle or loosen contents) while keeping the grasp.

## When to use

The grasp must be tested or contents shaken while holding.

## Not to be confused with

- `stir`: stir moves a utensil inside a container; shake moves the held object itself.

## Inputs

- `object` (`object_ref`): The right-held object.

## Applicability

Requires holding(hand=right, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `shaken(object=$object)` — The held object was oscillated at least three times with >= 2 cm amplitude without slipping. GT: robot_memory (TCP oscillation + hold checks).
- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `shaken(object=$object)` (all paths)
- `holding(hand=right, object=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `lateral` — when always (default path)

1. `policy_102($object)`

## Relations

- Next step: `pour` (`skill_039`) (enables) — loose contents are poured out
- Alternative: `rotate` (`skill_025`) — the orientation, not the contents, matters

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_070`.
