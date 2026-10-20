---
name: upright-object
description: "Make a lying object stand: pinch it, rotate its local up axis to vertical in the hand, and set it down upright on the same support."
---

# Stand an object upright (`skill_036`)

`upright(object: object_ref)`

Make a lying object stand: pinch it, rotate its local up axis to vertical in the hand, and set it down upright on the same support.

## When to use

A lying object must stand on its base again.

## Not to be confused with

- `tip`: opposite direction.

## Inputs

- `object` (`object_ref`): A lying object.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object); lying(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `lying(object=$object)` — Object on its side: longest axis within 60 deg of horizontal and vertical extent <= 60 % of its length. GT: object_pose, asset_annotation.

## Postconditions (verified on live GT state)

- `upright(object=$object)` — Object z axis within 20 deg of vertical. GT: object_pose.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `upright(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)
- `on(object=$object, support=@object.support)` (path pick_orient_place)

## May invalidate

`lying($object)`

## Policy paths (first match on the bound nouns)

### `pick_orient_place` — when 'top_pinch' in object.grasp_types

1. `policy_010($object)`
2. `policy_054($object, max_tilt_deg=15.0)`
3. `policy_015($object, @object.support, hint=@object.xy)`
- extra postcondition `on(object=$object, support=@object.support)`
- Set down where it lay: a free edge spot near the robot had no IK for the sideways grip the turn leaves on the upright object.

## Relations

- Next step: `pick` (`skill_017`) (enables) — the standing object is then grasped by its top
- Is a fallback for: `pick` (`skill_017`) (recover) — a tall object fell over and its top pinch is gone
- Alternative: `tip` (`skill_035`) — opposite effect

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_044`.
