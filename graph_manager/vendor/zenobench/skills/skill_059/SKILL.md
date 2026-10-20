---
name: count-category
description: "Sweep the head from the current place and count the visible objects whose asset or tag matches."
---

# Count objects of a category (`skill_059`)

`count(category: tag)`

Sweep the head from the current place and count the visible objects whose asset or tag matches.

## When to use

The number of objects of one category in view must be known.

## Not to be confused with

- `identify`: count returns a number for one category.

## Inputs

- `category` (`tag`): Asset name or tag, e.g. "cherry_tomato", "fruit".

## Outputs

- `count` (`number`): Number of visible matches.
- `objects` (`object_list`): The matches.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `counted(category=$category)` — The robot recorded how many objects of the category it sees from its current place. GT: robot_memory, head_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `counted(category=$category)` (all paths)

## Policy paths (first match on the bound nouns)

### `head_sweep` — when always (default path)

1. `policy_112($category)`

## Relations

- Next step: `collect` (`skill_048`) (then) — the counted objects are gathered
- Fallback on failure: `explore` (`skill_014`) (recover) — objects of the category may be out of view

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_067`.
