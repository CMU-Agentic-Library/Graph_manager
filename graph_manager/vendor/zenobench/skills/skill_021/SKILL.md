---
name: release-object
description: Open one gripper where the object already rests (e.g. let go of a braced pot, or of an object that was set down by another action) and back the fingers off.
---

# Release an object (`skill_021`)

`release(object: object_ref, hand: hand)`

Open one gripper where the object already rests (e.g. let go of a braced pot, or of an object that was set down by another action) and back the fingers off.

## When to use

The hand must open in place (the object is already supported).

## Not to be confused with

- `drop`: drop moves above a container first; release does not move the object.
- `place`: place moves to a pose first; release only opens the hand.

## Inputs

- `object` (`object_ref`): The object in the hand.
- `hand` (`hand`, default 'right'): Which gripper opens.

## Applicability

Requires holding(hand=$hand, object=$object).

## Preconditions (checked on live GT state before moving)

- `holding(hand=$hand, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Postconditions (verified on live GT state)

- `hand_empty(hand=$hand)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `hand_empty(hand=$hand)` (all paths)

## May invalidate

`holding($hand,$object)`, `steadied($object)`

## Policy paths (first match on the bound nouns)

### `open_in_place` — when always (default path)

1. `policy_096($object, $hand)`

## Relations

- Previous step: `brace` (`skill_027`) (enables) — bracing is finished
- Previous step: `hover` (`skill_063`) (enables) — the object is let go right there
- Next step: `tuck` (`skill_009`) (enables) — the arm is folded after letting go
- Alternative: `drop` (`skill_019`) — the object should fall into a container

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_029`.
