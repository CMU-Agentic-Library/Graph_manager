---
name: arrange-objects
description: "Place the listed objects on one support so that they are pairwise within a distance (a place setting)."
---

# Arrange objects together (`skill_052`)

`arrange(objects: object_list, support: support_ref, max_dist_m: positive_number)`

Place the listed objects on one support so that they are pairwise within a distance (a place setting).

## When to use

Several objects must be grouped together on one support (a setting).

## Not to be confused with

- `sweep`: arrange picks and places; sweep pushes.

## Inputs

- `objects` (`object_list`): Objects to group.
- `support` (`support_ref`): The surface.
- `max_dist_m` (`positive_number`, default 0.5): Pairwise distance limit.

## Composite skill

Runs these Skill Contracts inside one call: `navigate`, `pick`, `place`.

- One call runs the whole chain of the selected path below; each nested step is a full Skill Contract (preconditions, policy, postconditions on GT state). It counts as a single Contract call.
- The chain includes its own navigation: there is no need to navigate or approach first.
- The first nested step that fails stops the call with SUBSKILL_FAILED; the error names the failed nested action. Nothing is repaired or retried, and steps that already succeeded are not undone, so objects may have moved or still be held.

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `grouped(objects=$objects, support=$support, max_dist_m=$max_dist_m)` — Every listed object is on the support and pairwise within the distance. GT: object_pose, support_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `grouped(objects=$objects, support=$support, max_dist_m=$max_dist_m)` (all paths)

## Policy paths (first match on the bound nouns)

### `place_near_common_spot` — when always (default path)

1. `for each item in $objects: [navigate](destination=$item) -> [pick](object=$item) -> [navigate](destination=$support) -> [place](object=$item, receptacle=$support, hint_xy=@support.roomiest_xy)`

## Relations

- Previous step: `clear` (`skill_050`) (then) — a new layout is set on the cleared surface
- Fallback on failure: `clear` (`skill_050`) (recover) — the support is too crowded

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_060`.
