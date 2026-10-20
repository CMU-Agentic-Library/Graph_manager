---
name: chill-food
description: Keep food in the closed refrigerator until it is at or below a target temperature.
---

# Chill food (`skill_044`)

`chill(food: object_ref, appliance: appliance_ref, temp_c: number)`

Keep food in the closed refrigerator until it is at or below a target temperature.

## When to use

Food or a drink must cool in the refrigerator.

## Not to be confused with

- `heat`: opposite direction, with the microwave or stove.

## Inputs

- `food` (`object_ref`): The food item with thermal state.
- `appliance` (`appliance_ref`, default 'breakfast_fridge'): The refrigerator.
- `temp_c` (`number`, default 8.0): Maximum temperature in degC.

## Outputs

- `temp_c` (`number`): Measured final temperature.

## Applicability

Requires in_appliance(object=$food, appliance=$appliance); is_closed(articulated=$appliance).

## Preconditions (checked on live GT state before moving)

- `in_appliance(object=$food, appliance=$appliance)` — Object centre inside the appliance cavity box (microwave) or body box (refrigerator). GT: object_pose, appliance_annotation.
- `is_closed(articulated=$appliance)` — Joint within 0.10 rad (doors) or 4 cm (drawers) of closed. GT: articulation_joint, articulation_annotation.

## Postconditions (verified on live GT state)

- `temperature_at_most(object=$food, temp_c=$temp_c)` — Task-level food temperature at or below the threshold. GT: thermal_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `temperature_at_most(object=$food, temp_c=$temp_c)` (all paths)

## Policy paths (first match on the bound nouns)

### `fridge_wait` — when appliance.category == 'refrigerator'

1. `policy_089($food, $temp_c, $appliance)`

## Relations

- Previous step: `close` (`skill_041`) (enables) — the fridge must be closed while cooling
- Next step: `open` (`skill_040`) (then) — the chilled food is taken out
- Fallback on failure: `close` (`skill_041`) (repair, repairs is_closed) — the fridge door is open

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_052`.
