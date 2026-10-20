---
name: pick-object
description: "Grasp one object with the right gripper and lift it. The grasp path is chosen from the object's GT annotation and state: microwave cavity grasp, floor corner pinch, slide-to-edge + edge pinch for flat items, handle pinch, rectangular or round rim pinch, top pinch, or a two-handed lift for wide items."
---

# Pick an object (`skill_017`)

`pick(object: object_ref, hands: hand?, grasp: tag?, pass_by: pose2d?)`

Grasp one object with the right gripper and lift it. The grasp path is chosen from the object's GT annotation and state: microwave cavity grasp, floor corner pinch, slide-to-edge + edge pinch for flat items, handle pinch, rectangular or round rim pinch, top pinch, or a two-handed lift for wide items.

## When to use

The robot must hold an object for any later hand action.

## Not to be confused with

- `regrasp`: regrasp improves a grasp on an object that is already held.
- `uncover`: uncover lifts a lid off its container and keeps it.
- `fetch`: fetch also navigates and places.

## Inputs

- `object` (`object_ref`): The object to grasp.
- `hands` (`hand`, optional): "both" requests a two-handed lift for wide items.
- `grasp` (`tag`, optional): Optional grasp style to request: handle, rim, top or edge.
- `pass_by` (`pose2d`, optional): Optional base waypoint: grasp while driving past.

## Outputs

- `grasp` (`hand`): Grasp route actually used.
- `lift_m` (`number`): Measured lift of the object.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object). Depending on the bound nouns, the chosen path also needs: microwave_cavity (object.location == 'microwave_cavity'): is_open(articulated=@object.appliance); inside_cabinet_or_fridge (object.location in ['refrigerator', 'cabinet']): is_open(articulated=@object.appliance); on_the_move (args.pass_by and 'top_pinch' in object.grasp_types): grasp_clearance(object=$object); two_hand_box (args.hands == 'both' and object.wide_box): hand_empty(hand=left); two_hand_flat (args.hands == 'both' and object.flat): hand_empty(hand=left); floor_top (object.on_floor and 'top_pinch' in object.grasp_types): on_floor(object=$object); flat_overhang_ready (object.flat and object.edge_ready): edge_overhang(object=$object); round_rim ('rim_pinch' in object.grasp_types): grasp_clearance(object=$object); top_pinch ('top_pinch' in object.grasp_types): grasp_clearance(object=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `holding(hand=right, object=$object)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `holding(hand=right, object=$object)` (all paths)
- `holding(hand=left, object=$object)` (path two_hand_box)
- `holding(hand=left, object=$object)` (path two_hand_flat)

## May invalidate

`on($object,*)`, `inside($object,*)`, `on_top_of($object,*)`, `on_floor($object)`, `hand_empty(right)`, `grasp_clearance($object)`, `edge_overhang($object)`, `at_initial_place($object)`, `arm_stowed(right)`, `in_appliance($object,*)`, `on_burner($object,*)`, `covered(*,$object)`

## Policy paths (first match on the bound nouns)

### `microwave_cavity` — when object.location == 'microwave_cavity'

1. `policy_048($object, @object.appliance)`
- extra precondition `is_open(articulated=@object.appliance)`
- Front withdrawal through the open door.

### `inside_cabinet_or_fridge` — when object.location in ['refrigerator', 'cabinet']

1. `policy_061($object)`
- extra precondition `is_open(articulated=@object.appliance)`
- Annotation-selected grasp through the opened door.

### `handle_requested` — when args.grasp == 'handle' and 'handle_pinch' in object.grasp_types and object.handle_collider

1. `policy_055($object)`
- Handle pinch on request; a container held by its handle can swing, so carry it gently.

### `on_the_move` — when args.pass_by and 'top_pinch' in object.grasp_types

1. `policy_052($object, $pass_by)`
- extra precondition `grasp_clearance(object=$object)`

### `two_hand_box` — when args.hands == 'both' and object.wide_box

1. `policy_057($object)`
- extra precondition `hand_empty(hand=left)`
- extra postcondition `holding(hand=left, object=$object)`

### `two_hand_flat` — when args.hands == 'both' and object.flat

1. `policy_045($object)`
2. `policy_056($object)`
- extra precondition `hand_empty(hand=left)`
- extra postcondition `holding(hand=left, object=$object)`

### `floor_top` — when object.on_floor and 'top_pinch' in object.grasp_types

1. `policy_065($object)`
2. `policy_042($object)`
3. `policy_010($object)`
- extra precondition `on_floor(object=$object)`
- Approach, lower the torso and lean over the item, then pinch it from above. Flat objects lying on the floor (books, notebooks) have no pick path: the parallel gripper cannot get a pad under or across them.

### `flat_overhang_ready` — when object.flat and object.edge_ready

1. `policy_013($object)`
- extra precondition `edge_overhang(object=$object)`
- The overhang already exists (e.g. after expose): pinch it directly.

### `flat_edge` — when object.flat

1. `policy_045($object)`
2. `policy_013($object)`
- Slide the flat item until it overhangs a free edge, then pinch the overhang.

### `rect_rim` — when 'rim_pinch_rect' in object.grasp_types

1. `policy_012($object)`

### `round_rim` — when 'rim_pinch' in object.grasp_types

1. `policy_011($object)`
- extra precondition `grasp_clearance(object=$object)`
- Preferred for cups, mugs, bowls and pots: a rim pinch does not let the vessel swing.

### `handle` — when 'handle_pinch' in object.grasp_types and object.handle_collider

1. `policy_055($object)`

### `top_pinch` — when 'top_pinch' in object.grasp_types

1. `policy_010($object)`
- extra precondition `grasp_clearance(object=$object)`

### `annotation_dispatch` — when object.grasp_types

1. `policy_061($object)`
- Any other annotated pinch: the general dispatcher selects it.

## Relations

- Previous step: `approach` (`skill_002`) (then) — the target is an object to grasp
- Previous step: `crouch` (`skill_005`) (then) — the object is on the floor or a low shelf
- Previous step: `inspect` (`skill_012`) (then) — an object found inside must be taken out
- Previous step: `drop` (`skill_019`) (enables) — more items go into the same container
- Previous step: `stack` (`skill_020`) (enables) — a taller stack is built
- Previous step: `handover` (`skill_022`) (enables) — a second object is picked with the free right hand
- Previous step: `push` (`skill_029`) (then) — the object was pushed into a graspable spot
- Previous step: `pull` (`skill_030`) (then) — the object is now close enough to grasp
- Previous step: `expose` (`skill_031`) (enables) — pinch the overhang
- Previous step: `separate` (`skill_032`) (enables) — grasp the freed object
- Previous step: `center` (`skill_033`) (then) — the secured object is grasped later
- Previous step: `roll` (`skill_034`) (then) — the rolled object is then grasped
- Previous step: `tip` (`skill_035`) (then) — the lying object is pinched across its side
- Previous step: `upright` (`skill_036`) (enables) — the standing object is then grasped by its top
- Previous step: `open` (`skill_040`) (enables) — an object inside must be taken out
- Previous step: `heat` (`skill_043`) (then) — the heated food is served
- Previous step: `uncover` (`skill_046`) (enables) — something inside is taken out
- Previous step: `measure` (`skill_058`) (then) — the size decides the grasp
- Previous step: `touch` (`skill_065`) (enables) — the touched object is then grasped
- Previous step: `stop` (`skill_068`) (enables) — the food is taken off the heat
- Next step: `navigate` (`skill_001`) (then) — the object must be carried elsewhere
- Next step: `place` (`skill_018`) (enables) — the object goes onto a surface or into a container
- Next step: `lift` (`skill_023`) (enables) — the object must clear a high rim while carried
- Fallback on failure: `expose` (`skill_031`) (repair, repairs edge_overhang) — a flat object cannot be pinched from the top: push it to the edge by hand, then pick the overhang
- Fallback on failure: `separate` (`skill_032`) (repair, repairs grasp_clearance) — fingers have no room beside the object (grasp_clearance false)
- Fallback on failure: `pull` (`skill_030`) (recover) — the object sits too deep to reach
- Fallback on failure: `approach` (`skill_002`) (recover) — no grasp is reachable from base poses near the current one
- Fallback on failure: `upright` (`skill_036`) (recover) — a tall object fell over and its top pinch is gone
- Fallback on failure: `crouch` (`skill_005`) (recover) — the object is on the floor or a low shelf
- Fallback on failure: `uncover` (`skill_046`) (recover) — the object to take is a lid-covered container's content
- Fallback on failure: `open` (`skill_040`) (repair, repairs is_open) — the object is inside a closed cabinet or appliance
- Is a fallback for: `stack` (`skill_020`) (recover) — the base's top is occupied: remove the top object first
- Alternative: `regrasp` (`skill_026`) — the object is already in the hand but badly held

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.

- no reachable grasp from any base pose
- object not held after lift (slipped)
- no free support edge for a flat object

Paired Contract: `contract_025`.
