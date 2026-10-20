---
name: stop-appliance
description: "Switch an appliance's heat off: press the stove power key off, or open the microwave door, which ends its cycle."
---

# Stop an appliance (`skill_068`)

`stop(appliance: appliance_ref)`

Switch an appliance's heat off: press the stove power key off, or open the microwave door, which ends its cycle.

## When to use

An appliance that is heating must be switched off.

## Not to be confused with

- `press`: press does not guarantee the heat is off.
- `close`: close does not stop a stove.

## Inputs

- `appliance` (`appliance_ref`): kitchen_stove or kitchen_microwave.

## Applicability

Requires hand_empty(hand=right); base_near(place=$appliance).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$appliance)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `not heating(appliance=$appliance)` — The appliance's heat source is on (microwave cycle or stove burner). GT: thermal_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `not heating(appliance=$appliance)` (all paths)
- `is_open(articulated=$appliance)` (path microwave_door)

## Policy paths (first match on the bound nouns)

### `stove_key_off` — when appliance.category == 'stove'

1. `policy_094(@appliance.power_button, state=False)`

### `microwave_door` — when appliance.category == 'microwave'

1. `policy_024($appliance)`
- extra postcondition `is_open(articulated=$appliance)`

## Relations

- Next step: `pick` (`skill_017`) (enables) — the food is taken off the heat
- Alternative: `heat` (`skill_043`) — heat stops automatically at a target temperature

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_076`.
