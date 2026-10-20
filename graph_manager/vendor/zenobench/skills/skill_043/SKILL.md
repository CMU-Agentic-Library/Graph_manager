---
name: heat-food
description: "Bring food to a target temperature with an appliance and switch the heat off: in the closed microwave (start key + wait) or in a pot on the stove burner (power key on, wait, power key off)."
---

# Heat food (`skill_043`)

`heat(food: object_ref, appliance: appliance_ref, temp_c: number)`

Bring food to a target temperature with an appliance and switch the heat off: in the closed microwave (start key + wait) or in a pot on the stove burner (power key on, wait, power key off).

## When to use

Food must reach a target temperature with the microwave or the stove.

## Not to be confused with

- `chill`: opposite direction, in the refrigerator.
- `press`: press does not wait.

## Inputs

- `food` (`object_ref`): The food item (has task-level thermal state).
- `appliance` (`appliance_ref`): kitchen_microwave or kitchen_stove.
- `temp_c` (`number`, default 60.0): Target temperature in degC.

## Outputs

- `temp_c` (`number`): Measured final temperature.

## Applicability

Requires hand_empty(hand=right); base_near(place=$appliance). Depending on the bound nouns, the chosen path also needs: microwave (appliance.category == 'microwave'): in_appliance(object=$food, appliance=$appliance), is_closed(articulated=$appliance); stove_pot (appliance.category == 'stove'): in_cookware_on_burner(food=$food, appliance=$appliance).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$appliance)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `temperature_at_least(object=$food, temp_c=$temp_c)` — Task-level food temperature at or above the threshold. GT: thermal_state.
- `not heating(appliance=$appliance)` — The appliance's heat source is on (microwave cycle or stove burner). GT: thermal_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `temperature_at_least(object=$food, temp_c=$temp_c)` (all paths)
- `not heating(appliance=$appliance)` (all paths)

## Policy paths (first match on the bound nouns)

### `microwave` — when appliance.category == 'microwave'

1. `policy_032($appliance)`
2. `policy_064($food, $temp_c)`
- extra precondition `in_appliance(object=$food, appliance=$appliance)`
- extra precondition `is_closed(articulated=$appliance)`

### `stove_pot` — when appliance.category == 'stove'

1. `policy_094(@appliance.power_button, state=True)`
2. `policy_090($food, $temp_c, $appliance)`
- extra precondition `in_cookware_on_burner(food=$food, appliance=$appliance)`
- Food must be inside a pot (or pan) whose bottom rests on the burner.

## Relations

- Previous step: `place` (`skill_018`) (enables) — the food went into the microwave or onto the stove
- Previous step: `stir` (`skill_038`) (then) — the stirred food is heated
- Previous step: `close` (`skill_041`) (enables) — a microwave or fridge must be closed before its cycle
- Previous step: `press` (`skill_042`) (enables) — the start key began a cycle
- Previous step: `cover` (`skill_045`) (enables) — the covered pot is heated
- Next step: `open` (`skill_040`) (then) — the heated food is taken out of the microwave
- Next step: `pick` (`skill_017`) (then) — the heated food is served
- Fallback on failure: `close` (`skill_041`) (repair, repairs is_closed) — the microwave door is open
- Fallback on failure: `place` (`skill_018`) (repair, repairs in_appliance) — the food is not in the appliance
- Fallback on failure: `wait` (`skill_056`) (recover) — the food is still below the target when the time budget ends
- Fallback on failure: `pour` (`skill_039`) (recover) — the food is in a cup, not in the pot on the burner
- Alternative: `heat` (`skill_043`) — no microwave is available: heat in a pot on the stove
- Alternative: `stop` (`skill_068`) — heat stops automatically at a target temperature

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_051`.
