---
name: search-object
description: "Find an object whose location is unknown: visit the supports of a room in order of distance and aim the head at each surface until the object is seen."
---

# Search for an object (`skill_013`)

`search(object: object_ref, region: room_ref?)`

Find an object whose location is unknown: visit the supports of a room in order of distance and aim the head at each surface until the object is seen.

## When to use

The location of an object is unknown in the current room.

## Not to be confused with

- `explore`: explore covers a room without a target.

## Inputs

- `object` (`object_ref`): The object to find.
- `region` (`room_ref`, optional): Room to search; default the robot's room.

## Outputs

- `found_on` (`support_ref`): Support under the object when it was seen.
- `visited` (`object_list`): Furniture visited in order.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `observed(target=$object)` — The robot saw the target in its head camera during this episode (set by look, search, inspect, explore). GT: robot_memory.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `observed(target=$object)` (all paths)

## May invalidate

`base_near(*)`, `reachable(*)`, `facing(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `room_sweep` — when always (default path)

1. `policy_070($object, $region)`

## Relations

- Previous step: `explore` (`skill_014`) (then) — a specific object must then be located
- Next step: `navigate` (`skill_001`) (then) — the found object must be fetched
- Fallback on failure: `explore` (`skill_014`) (recover) — the object is not on any visited support
- Fallback on failure: `inspect` (`skill_012`) (substitute) — the object may be inside a closed cabinet
- Is a fallback for: `fetch` (`skill_047`) (recover) — the object is not where expected

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_021`.
