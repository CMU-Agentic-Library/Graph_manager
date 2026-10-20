---
name: close-articulated
description: Close a door, drawer or appliance door to within 0.10 rad / 4 cm of closed. A powered microwave door closes from its hinge-clearance pose, also while the robot carries a load.
---

# Close a door or drawer (`skill_041`)

`close(articulated: articulated_ref)`

Close a door, drawer or appliance door to within 0.10 rad / 4 cm of closed. A powered microwave door closes from its hinge-clearance pose, also while the robot carries a load.

## When to use

A door, drawer or appliance must be closed (before heating, after taking out).

## Not to be confused with

- `open`: opposite direction.

## Inputs

- `articulated` (`articulated_ref`): The open part.

## Outputs

- `joint` (`number`): Measured joint value.

## Applicability

Requires base_near(place=$articulated). Depending on the bound nouns, the chosen path also needs: handle_push (articulated.has_handle): hand_empty(hand=right); dispatch (always (default path)): hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `base_near(place=$articulated)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `is_closed(articulated=$articulated)` — Joint within 0.10 rad (doors) or 4 cm (drawers) of closed. GT: articulation_joint, articulation_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `is_closed(articulated=$articulated)` (all paths)

## May invalidate

`is_open($articulated)`, `base_near(*)`, `reachable(*)`, `facing(*)`

## Policy paths (first match on the bound nouns)

### `powered_loaded` — when articulated.powered and robot.right_held

1. `policy_030($articulated)`
2. `policy_031($articulated, target=close)`

### `powered` — when articulated.powered

1. `policy_025($articulated)`

### `handle_push` — when articulated.has_handle

1. `policy_003()`
2. `policy_023($articulated)`
- extra precondition `hand_empty(hand=right)`

### `dispatch` — when always (default path)

1. `policy_063($articulated)`
- extra precondition `hand_empty(hand=right)`

## Relations

- Previous step: `place` (`skill_018`) (enables) — the object went into a cabinet or appliance whose door must be shut
- Previous step: `open` (`skill_040`) (then) — the door must be shut afterwards
- Previous step: `collect` (`skill_048`) (then) — the container sits in a cabinet that must be closed
- Previous step: `sort` (`skill_049`) (then) — a sorted container sits in a cabinet
- Next step: `heat` (`skill_043`) (enables) — a microwave or fridge must be closed before its cycle
- Next step: `chill` (`skill_044`) (enables) — the fridge must be closed while cooling
- Next step: `navigate` (`skill_001`) (then) — the robot leaves
- Fallback on failure: `retreat` (`skill_004`) (recover) — the door swing hits the base
- Is a fallback for: `heat` (`skill_043`) (repair) — the microwave door is open
- Is a fallback for: `chill` (`skill_044`) (repair) — the fridge door is open

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_049`.
