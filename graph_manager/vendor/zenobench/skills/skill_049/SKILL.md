---
name: sort-objects
description: Put each listed object into the container mapped to its category tag (e.g. fruit -> basket, toy -> toy box).
---

# Sort objects by category (`skill_049`)

`sort(objects: object_list, rule: category_map)`

Put each listed object into the container mapped to its category tag (e.g. fruit -> basket, toy -> toy box).

## When to use

Objects must go to destinations by category.

## Not to be confused with

- `collect`: sort chooses a destination per category.

## Inputs

- `objects` (`object_list`): Objects to sort.
- `rule` (`category_map`): Tag -> destination mapping (a container or a support), e.g. {"fruit": "fruit_basket"}.

## Composite skill

Runs these Skill Contracts inside one call: `fetch`, `navigate`, `pick`, `place`.

- One call runs the whole chain of the selected path below; each nested step is a full Skill Contract (preconditions, policy, postconditions on GT state). It counts as a single Contract call.
- The chain includes its own navigation: there is no need to navigate or approach first.
- The first nested step that fails stops the call with SUBSKILL_FAILED; the error names the failed nested action. Nothing is repaired or retried, and steps that already succeeded are not undone, so objects may have moved or still be held.

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `sorted_by_category(objects=$objects, rule=$rule)` — Each listed object is inside the container (or on the support) mapped to one of its tags. GT: object_pose, asset_tags, container_profile.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `sorted_by_category(objects=$objects, rule=$rule)` (all paths)

## Policy paths (first match on the bound nouns)

### `fetch_by_tag` — when always (default path)

1. `for each item in $objects: [fetch](object=$item, receptacle=@item.sort_target)`

## Relations

- Previous step: `identify` (`skill_057`) (then) — the category decides the destination
- Next step: `close` (`skill_041`) (then) — a sorted container sits in a cabinet
- Alternative: `collect` (`skill_048`) — all objects go into one container

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_057`.
