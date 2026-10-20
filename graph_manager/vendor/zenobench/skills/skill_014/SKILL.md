---
name: explore-room
description: "Cover a room from up to three viewpoints with a left/centre/right head sweep; succeeds when at least 75 % of the room's supports and objects were seen."
---

# Explore a room (`skill_014`)

`explore(room: room_ref)`

Cover a room from up to three viewpoints with a left/centre/right head sweep; succeeds when at least 75 % of the room's supports and objects were seen.

## When to use

A room must be surveyed before planning (unknown layout or objects).

## Not to be confused with

- `search`: search looks for one object and stops when found.

## Inputs

- `room` (`room_ref`): The room to cover.

## Outputs

- `seen` (`object_list`): Objects observed during the sweep.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `room_explored(room=$room)` — At least 75 % of the room's head-camera viewpoints were covered. GT: robot_memory, room_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `room_explored(room=$room)` (all paths)

## May invalidate

`base_near(*)`, `reachable(*)`, `facing(*)`, `in_view(*)`

## Policy paths (first match on the bound nouns)

### `viewpoints` — when always (default path)

1. `policy_069($room)`

## Relations

- Next step: `search` (`skill_013`) (then) — a specific object must then be located
- Is a fallback for: `search` (`skill_013`) (recover) — the object is not on any visited support
- Is a fallback for: `count` (`skill_059`) (recover) — objects of the category may be out of view

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_022`.
