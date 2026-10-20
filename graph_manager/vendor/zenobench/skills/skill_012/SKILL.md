---
name: inspect-receptacle
description: Look into a container, a cabinet, an appliance cavity or onto a support and report the objects inside or on it. A closed cabinet is opened for the look and closed again.
---

# Inspect a receptacle (`skill_012`)

`inspect(receptacle: entity_ref)`

Look into a container, a cabinet, an appliance cavity or onto a support and report the objects inside or on it. A closed cabinet is opened for the look and closed again.

## When to use

The contents of a container or cabinet must be seen (opens it if needed).

## Not to be confused with

- `look`: look reports nothing about contents.
- `search`: inspect examines one given receptacle; search chooses where to look.

## Inputs

- `receptacle` (`entity_ref`): Container, articulated cabinet/appliance or support to examine.

## Outputs

- `contents` (`object_list`): Objects found inside/on the receptacle and visible.

## Applicability

Requires base_near(place=$receptacle). Depending on the bound nouns, the chosen path also needs: closed_cabinet (receptacle.kind == 'articulated' and not receptacle.is_open): hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `base_near(place=$receptacle)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `observed(target=$receptacle)` — The robot saw the target in its head camera during this episode (set by look, search, inspect, explore). GT: robot_memory.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `observed(target=$receptacle)` (all paths)

## Policy paths (first match on the bound nouns)

### `closed_cabinet` — when receptacle.kind == 'articulated' and not receptacle.is_open

1. `policy_003()`
2. `policy_062($receptacle)`
3. `policy_088($receptacle)`
4. `policy_003()`
5. `policy_063($receptacle)`
- extra precondition `hand_empty(hand=right)`
- Open with the annotation-selected route, look, close again.

### `open_view` — when always (default path)

1. `policy_088($receptacle)`

## Relations

- Next step: `pick` (`skill_017`) (then) — an object found inside must be taken out
- Next step: `empty` (`skill_051`) (then) — every object inside must be removed
- Is a fallback for: `search` (`skill_013`) (substitute) — the object may be inside a closed cabinet
- Alternative: `look` (`skill_011`) — only the receptacle itself must be seen

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_020`.
