---
name: tip-object
description: "Push a standing tall object near its top so it falls onto its side on the same support (lays down a carton or bottle that is too tall to top-pinch)."
---

# Tip an object over (`skill_035`)

`tip(object: object_ref)`

Push a standing tall object near its top so it falls onto its side on the same support (lays down a carton or bottle that is too tall to top-pinch).

## When to use

An upright object must be laid on its side.

## Not to be confused with

- `upright`: upright makes a lying object stand.

## Inputs

- `object` (`object_ref`): A standing tall object.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object); upright(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `upright(object=$object)` — Object z axis within 20 deg of vertical. GT: object_pose.

## Postconditions (verified on live GT state)

- `lying(object=$object)` — Object on its side: longest axis within 60 deg of horizontal and vertical extent <= 60 % of its length. GT: object_pose, asset_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `lying(object=$object)` (all paths)

## May invalidate

`upright($object)`, `at_initial_place($object)`

## Policy paths (first match on the bound nouns)

### `push_high` — when object.tall

1. `policy_082($object)`

## Relations

- Next step: `roll` (`skill_034`) (enables) — the lying cylinder is rolled
- Next step: `pick` (`skill_017`) (then) — the lying object is pinched across its side
- Alternative: `upright` (`skill_036`) — opposite effect

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_043`.
