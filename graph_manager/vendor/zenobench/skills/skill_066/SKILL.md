---
name: knock-articulated
description: "Tap a closed door or drawer panel twice with the closed fingertips beside its handle; the panel must stay closed."
---

# Knock on a door (`skill_066`)

`knock(articulated: articulated_ref)`

Tap a closed door or drawer panel twice with the closed fingertips beside its handle; the panel must stay closed.

## When to use

A closed door must be knocked on (check, signal) without opening it.

## Not to be confused with

- `open`: knock must leave the door closed.

## Inputs

- `articulated` (`articulated_ref`): The closed door or drawer.

## Applicability

Requires hand_empty(hand=right); base_near(place=$articulated); is_closed(articulated=$articulated).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$articulated)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `is_closed(articulated=$articulated)` — Joint within 0.10 rad (doors) or 4 cm (drawers) of closed. GT: articulation_joint, articulation_annotation.

## Postconditions (verified on live GT state)

- `knocked(articulated=$articulated)` — Two measured fingertip contacts on the closed panel during the Contract; the joint moved < 0.05. GT: event_log (fingertip contact), articulation_joint.
- `is_closed(articulated=$articulated)` — Joint within 0.10 rad (doors) or 4 cm (drawers) of closed. GT: articulation_joint, articulation_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `knocked(articulated=$articulated)` (all paths)
- `is_closed(articulated=$articulated)` (all paths)

## Policy paths (first match on the bound nouns)

### `panel_taps` — when articulated.has_handle

1. `policy_106($articulated)`

## Relations

- Next step: `open` (`skill_040`) (then) — the door is opened after knocking
- Alternative: `touch` (`skill_065`) — an object, not a door, is to be tapped

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_074`.
