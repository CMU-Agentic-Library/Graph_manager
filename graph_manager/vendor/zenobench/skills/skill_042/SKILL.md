---
name: press-button
description: Press an annotated appliance button with the closed fingertips and retract: the microwave door key, the microwave start key, or the stove power key (which toggles the burner).
---

# Press a button (`skill_042`)

`press(button: button_ref)`

Press an annotated appliance button with the closed fingertips and retract: the microwave door key, the microwave start key, or the stove power key (which toggles the burner).

## When to use

A button (microwave keys, stove power key) must be pressed.

## Not to be confused with

- `heat`: heat guarantees a temperature; press guarantees only the key press.
- `open`: open guarantees the door is open.

## Inputs

- `button` (`button_ref`): E.g. kitchen_microwave/door_button, kitchen_stove/power_button.

## Applicability

Requires hand_empty(hand=right); base_near(place=@button.appliance). Depending on the bound nouns, the chosen path also needs: microwave_start_staged (button.button == 'start_button'): is_closed(articulated=@button.appliance).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=@button.appliance)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `button_pressed(button=$button)` — A measured press of this button happened during the Contract. GT: event_log (measured fingertip contact).
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `button_pressed(button=$button)` (all paths)
- `hand_empty(hand=right)` (all paths)
- `heating(appliance=@button.appliance)` (path microwave_start_staged)

## May invalidate

`arm_stowed(right)`, `reachable(*)`

## Policy paths (first match on the bound nouns)

### `microwave_start_staged` — when button.button == 'start_button'

1. `policy_027(@button.appliance, button=start)`
2. `policy_028(@button.appliance, button=start)`
3. `policy_029(@button.appliance, button=start)`
- extra precondition `is_closed(articulated=@button.appliance)`
- extra postcondition `heating(appliance=@button.appliance)`

### `microwave_door_key` — when button.button == 'door_button'

1. `policy_033(@button.appliance, button=door)`

### `generic_key` — when always (default path)

1. `policy_094($button)`

## Relations

- Previous step: `approach` (`skill_002`) (then) — the target is a button
- Next step: `heat` (`skill_043`) (enables) — the start key began a cycle
- Next step: `tuck` (`skill_009`) (enables) — the hand is free again
- Alternative: `open` (`skill_040`) — the door key is pressed only to open the microwave door

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_050`.
