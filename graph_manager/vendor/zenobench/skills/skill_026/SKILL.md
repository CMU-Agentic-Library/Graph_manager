---
name: regrasp-object
description: Set the held object down on a support and grasp it again with a fresh, centred grasp (recovery when the object has pivoted in the pinch).
---

# Regrasp a held object (`skill_026`)

`regrasp(object: object_ref, support: support_ref)`

Set the held object down on a support and grasp it again with a fresh, centred grasp (recovery when the object has pivoted in the pinch).

## When to use

The current grasp is unsuitable (wrong end, slipping) and the object can be set down.

## Not to be confused with

- `pick`: pick starts from an empty hand.
- `rotate`: rotate keeps the grasp; regrasp sets the object down and grasps again.

## Inputs

- `object` (`object_ref`): The held object.
- `support` (`support_ref`): Where to set it down briefly.

## Outputs

- `grasp` (`hand`): Grasp kind after the regrasp.

## Applicability

Requires holding(hand=right, object=$object); base_near(place=$support).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$support)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `holding(hand=right, object=$object)` (all paths)

## Policy paths (first match on the bound nouns)

### `set_down_and_pick` — when always (default path)

1. `policy_076($object, $support)`

## Relations

- Next step: `place` (`skill_018`) (enables) — the corrected grasp is used to place precisely
- Is a fallback for: `place` (`skill_018`) (recover) — the object turned in the hand and no longer clears the target
- Alternative: `pick` (`skill_017`) — the object is already in the hand but badly held
- Alternative: `rotate` (`skill_025`) — the grasp, not the yaw, must change

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_034`.
