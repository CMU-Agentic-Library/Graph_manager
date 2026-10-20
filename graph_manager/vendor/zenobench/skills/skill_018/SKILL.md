---
name: place-object
description: "Put the right-held object down on a support surface or into an open container and release it. The path follows the receptacle and grasp: microwave cavity (insert, release, withdraw), container, edge-held flat object slid back over an edge, ordinary surface (optionally near a hint point), or while driving past."
---

# Place a held object (`skill_018`)

`place(object: object_ref, receptacle: receptacle_ref, hint_xy: xy?, pass_by: pose2d?)`

Put the right-held object down on a support surface or into an open container and release it. The path follows the receptacle and grasp: microwave cavity (insert, release, withdraw), container, edge-held flat object slid back over an edge, ordinary surface (optionally near a hint point), or while driving past.

## When to use

A held object must end up resting on a support, in a container or on a burner.

## Not to be confused with

- `drop`: drop releases above a container opening without lowering.
- `stack`: stack targets another object's top face.
- `release`: release opens the fingers where the object already rests.

## Inputs

- `object` (`object_ref`): The held object.
- `receptacle` (`receptacle_ref`): A support surface or an open container.
- `hint_xy` (`xy`, optional): Optional preferred position on a surface.
- `pass_by` (`pose2d`, optional): Optional base waypoint: place while driving past.

## Outputs

- `position` (`xy`): Measured bottom position after release.

## Applicability

Requires holding(hand=right, object=$object); base_near(place=$receptacle). Depending on the bound nouns, the chosen path also needs: microwave_staged (receptacle.kind == 'support' and receptacle.is_microwave_cavity and robot.right_kind == 'pinch'): is_open(articulated=kitchen_microwave); microwave (receptacle.kind == 'support' and receptacle.is_microwave_cavity): is_open(articulated=kitchen_microwave); cabinet_or_fridge_shelf (receptacle.kind == 'support' and receptacle.category == 'cabinet_inside' and receptacle.appliance): is_open(articulated=@receptacle.appliance); container (receptacle.kind == 'object'): uncovered(container=$receptacle).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$receptacle)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `hand_empty(hand=right)` (all paths)
- `on(object=$object, support=$receptacle)` (path microwave_staged)
- `in_appliance(object=$object, appliance=kitchen_microwave)` (path microwave_staged)
- `on(object=$object, support=$receptacle)` (path microwave)
- `in_appliance(object=$object, appliance=kitchen_microwave)` (path microwave)
- `on(object=$object, support=$receptacle)` (path cabinet_or_fridge_shelf)
- `inside(object=$object, container=$receptacle)` (path container)
- `on(object=$object, support=$receptacle)` (path on_the_move)
- `on(object=$object, support=$receptacle)` (path edge_held_flat)
- `on(object=$object, support=$receptacle)` (path stove_burner)
- `on_burner(object=$object, appliance=@receptacle.appliance)` (path stove_burner)
- `on(object=$object, support=$receptacle)` (path surface)

## May invalidate

`holding(right,$object)`, `presenting($object)`, `base_clear_of(*)`

## Policy paths (first match on the bound nouns)

### `microwave_staged` — when receptacle.kind == 'support' and receptacle.is_microwave_cavity and robot.right_kind == 'pinch'

1. `policy_018($object, $receptacle)`
2. `policy_019($object)`
3. `policy_020($object)`
- extra precondition `is_open(articulated=kitchen_microwave)`
- extra postcondition `on(object=$object, support=$receptacle)`
- extra postcondition `in_appliance(object=$object, appliance=kitchen_microwave)`

### `microwave` — when receptacle.kind == 'support' and receptacle.is_microwave_cavity

1. `policy_021($object, $receptacle)`
- extra precondition `is_open(articulated=kitchen_microwave)`
- extra postcondition `on(object=$object, support=$receptacle)`
- extra postcondition `in_appliance(object=$object, appliance=kitchen_microwave)`

### `cabinet_or_fridge_shelf` — when receptacle.kind == 'support' and receptacle.category == 'cabinet_inside' and receptacle.appliance

1. `policy_015($object, $receptacle, hint=$hint_xy)`
- extra precondition `is_open(articulated=@receptacle.appliance)`
- extra postcondition `on(object=$object, support=$receptacle)`

### `container` — when receptacle.kind == 'object'

1. `policy_016($object, $receptacle)`
- extra precondition `uncovered(container=$receptacle)`
- extra postcondition `inside(object=$object, container=$receptacle)`

### `on_the_move` — when receptacle.kind == 'support' and args.pass_by

1. `policy_053($object, $receptacle, $pass_by, xy=$hint_xy)`
- extra postcondition `on(object=$object, support=$receptacle)`

### `edge_held_flat` — when receptacle.kind == 'support' and robot.right_kind == 'edge'

1. `policy_017($object, $receptacle, hint=$hint_xy)`
- extra postcondition `on(object=$object, support=$receptacle)`

### `stove_burner` — when receptacle.kind == 'support' and receptacle.category == 'cooktop'

1. `policy_015($object, $receptacle, hint=@receptacle.burner_xy)`
- extra postcondition `on(object=$object, support=$receptacle)`
- extra postcondition `on_burner(object=$object, appliance=@receptacle.appliance)`
- Cookware goes centred on the burner disc so the stove can heat it.

### `surface` — when receptacle.kind == 'support'

1. `policy_015($object, $receptacle, hint=$hint_xy)`
- extra postcondition `on(object=$object, support=$receptacle)`

## Relations

- Previous step: `present` (`skill_016`) (enables) — the object is put away after showing it
- Previous step: `pick` (`skill_017`) (enables) — the object goes onto a surface or into a container
- Previous step: `lower` (`skill_024`) (enables) — the object goes onto a low shelf or into the fridge
- Previous step: `rotate` (`skill_025`) (enables) — the object is set down in the new orientation
- Previous step: `regrasp` (`skill_026`) (enables) — the corrected grasp is used to place precisely
- Previous step: `wipe` (`skill_037`) (enables) — the sponge is put back
- Previous step: `pour` (`skill_039`) (enables) — the empty cup is put down
- Previous step: `open` (`skill_040`) (enables) — an object must go inside
- Next step: `close` (`skill_041`) (enables) — the object went into a cabinet or appliance whose door must be shut
- Next step: `heat` (`skill_043`) (enables) — the food went into the microwave or onto the stove
- Next step: `tuck` (`skill_009`) (enables) — the hand is empty and the robot drives next
- Fallback on failure: `drop` (`skill_019`) (substitute) — a deep container leaves no room to lower the hand inside
- Fallback on failure: `approach` (`skill_002`) (recover) — the receptacle is out of reach
- Fallback on failure: `open` (`skill_040`) (repair, repairs is_open) — the receptacle is behind a closed door
- Fallback on failure: `uncover` (`skill_046`) (repair, repairs uncovered) — the container has its lid on
- Fallback on failure: `regrasp` (`skill_026`) (recover) — the object turned in the hand and no longer clears the target
- Is a fallback for: `heat` (`skill_043`) (repair) — the food is not in the appliance
- Alternative: `stack` (`skill_020`) — the object should rest on another object
- Alternative: `drop` (`skill_019`) — the target is a deep bin and a gentle release is not required

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.

- target unreachable
- container shifted before release
- object not on/in target after release

Paired Contract: `contract_026`.
