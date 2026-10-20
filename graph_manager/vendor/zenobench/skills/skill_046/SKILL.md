---
name: uncover-container
description: Lift the lid off a container by its knob and set it down beside the container: on the same support when it has room, else on the nearest counter-height support; the lid noun is found from GT (the lid resting on the rim).
---

# Uncover a container (`skill_046`)

`uncover(container: container_ref)`

Lift the lid off a container by its knob and set it down beside the container: on the same support when it has room, else on the nearest counter-height support; the lid noun is found from GT (the lid resting on the rim).

## When to use

A lid must be removed before reaching into or pouring into a container.

## Not to be confused with

- `pick`: uncover also puts the lid aside.

## Inputs

- `container` (`container_ref`): The covered container.

## Outputs

- `lid` (`lid_ref`): The lid that was removed.

## Applicability

Requires hand_empty(hand=right); base_near(place=$container).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$container)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `uncovered(container=$container)` — No lid rests on the container rim. GT: object_pose, container_profile, asset_tags.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `uncovered(container=$container)` (all paths)
- `hand_empty(hand=right)` (all paths)
- `on(object=@container.lid, support=@container.aside_support)` (path knob_lift_aside)

## May invalidate

`covered($container,*)`

## Policy paths (first match on the bound nouns)

### `knob_lift_aside` — when container.lid

1. `policy_010(@container.lid)`
2. `policy_015(@container.lid, @container.aside_support)`
- extra postcondition `on(object=@container.lid, support=@container.aside_support)`

## Relations

- Next step: `pour` (`skill_039`) (enables) — food is poured into the opened pot
- Next step: `stir` (`skill_038`) (enables) — the opened pot is stirred
- Next step: `pick` (`skill_017`) (enables) — something inside is taken out
- Is a fallback for: `pick` (`skill_017`) (recover) — the object to take is a lid-covered container's content
- Is a fallback for: `place` (`skill_018`) (repair) — the container has its lid on
- Is a fallback for: `pour` (`skill_039`) (repair) — the target has its lid on
- Is a fallback for: `empty` (`skill_051`) (repair) — the container has its lid on
- Alternative: `cover` (`skill_045`) — opposite effect

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_054`.
