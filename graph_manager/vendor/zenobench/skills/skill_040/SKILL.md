---
name: open-articulated
description: Open a door, drawer, refrigerator door or microwave door to its annotated open value. The path follows the part: powered microwave (door button + hinge), refrigerator handle, drawer handle pull, hinged door side-hook ride, or a door opened by the right hand while the left hand holds a load.
---

# Open a door or drawer (`skill_040`)

`open(articulated: articulated_ref)`

Open a door, drawer, refrigerator door or microwave door to its annotated open value. The path follows the part: powered microwave (door button + hinge), refrigerator handle, drawer handle pull, hinged door side-hook ride, or a door opened by the right hand while the left hand holds a load.

## When to use

A door, drawer or appliance must be opened before reaching inside.

## Not to be confused with

- `press`: press only pushes a button; open guarantees the door is open.

## Inputs

- `articulated` (`articulated_ref`): The door, drawer or appliance door.

## Outputs

- `joint` (`number`): Measured joint value.

## Applicability

Requires base_near(place=$articulated). Depending on the bound nouns, the chosen path also needs: powered_microwave (articulated.powered): hand_empty(hand=right); left_holds_load (robot.left_held and articulated.type == 'revolute'): hand_empty(hand=right); refrigerator (articulated.category == 'refrigerator'): hand_empty(hand=right); drawer (articulated.type == 'prismatic'): hand_empty(hand=right); hinged_door (articulated.type == 'revolute'): hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `base_near(place=$articulated)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `is_open(articulated=$articulated)` — Joint at least 60 % of the way from closed to its annotated open value. GT: articulation_joint, articulation_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `is_open(articulated=$articulated)` (all paths)

## May invalidate

`is_closed($articulated)`, `base_near(*)`, `reachable(*)`, `facing(*)`

## Policy paths (first match on the bound nouns)

### `powered_microwave` — when articulated.powered

1. `policy_024($articulated)`
- extra precondition `hand_empty(hand=right)`

### `left_holds_load` — when robot.left_held and articulated.type == 'revolute'

1. `policy_060(@robot.left_object, $articulated)`
- extra precondition `hand_empty(hand=right)`

### `refrigerator` — when articulated.category == 'refrigerator'

1. `policy_003()`
2. `policy_022($articulated, goal=@articulated.wide_open_q)`
- extra precondition `hand_empty(hand=right)`
- Rides the door to 75 % of its annotated range (60 deg), wide enough to put a can on the shelf.

### `drawer` — when articulated.type == 'prismatic'

1. `policy_003()`
2. `policy_046($articulated)`
3. `policy_050($articulated)`
4. `policy_047($articulated)`
- extra precondition `hand_empty(hand=right)`

### `hinged_door` — when articulated.type == 'revolute'

1. `policy_003()`
2. `policy_046($articulated)`
3. `policy_049($articulated)`
4. `policy_047($articulated)`
- extra precondition `hand_empty(hand=right)`

## Relations

- Previous step: `approach` (`skill_002`) (then) — the target is a door or drawer
- Previous step: `retreat` (`skill_004`) (then) — a door's swing needs room in front of the robot
- Previous step: `handover` (`skill_022`) (enables) — the right hand must open a door while the left carries the load
- Previous step: `heat` (`skill_043`) (then) — the heated food is taken out of the microwave
- Previous step: `chill` (`skill_044`) (then) — the chilled food is taken out
- Previous step: `wait` (`skill_056`) (then) — a cycle finished and the door is opened
- Previous step: `knock` (`skill_066`) (then) — the door is opened after knocking
- Next step: `pick` (`skill_017`) (enables) — an object inside must be taken out
- Next step: `place` (`skill_018`) (enables) — an object must go inside
- Next step: `close` (`skill_041`) (then) — the door must be shut afterwards
- Fallback on failure: `retreat` (`skill_004`) (recover) — the door swing hits the base
- Fallback on failure: `handover` (`skill_022`) (repair, repairs hand_empty) — the right hand still holds a load
- Fallback on failure: `approach` (`skill_002`) (recover) — the handle is out of reach
- Is a fallback for: `pick` (`skill_017`) (repair) — the object is inside a closed cabinet or appliance
- Is a fallback for: `place` (`skill_018`) (repair) — the receptacle is behind a closed door
- Alternative: `press` (`skill_042`) — the door key is pressed only to open the microwave door

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_048`.
