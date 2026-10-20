---
name: expose-object
description: "Push a flat object (book, plate, notebook) until it overhangs a free support edge by >= 5.5 cm while its centre of mass stays on the support, so the overhang can be pinched."
---

# Expose a grasp edge (`skill_031`)

`expose(object: object_ref)`

Push a flat object (book, plate, notebook) until it overhangs a free support edge by >= 5.5 cm while its centre of mass stays on the support, so the overhang can be pinched.

## When to use

A flat object is wider than the gripper and must overhang an edge before pick.

## Not to be confused with

- `push`: expose pushes toward a free edge until a pinchable overhang exists.

## Inputs

- `object` (`object_ref`): A flat object on a support.

## Applicability

Requires hand_empty(hand=right); base_near(place=$object).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.
- `base_near(place=$object)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `edge_overhang(object=$object)` — A flat object overhangs a support edge enough for an edge pinch (>= 5.5 cm) while its centre of mass stays 3.5 cm inside the edge. GT: object_pose, asset_annotation, support_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `edge_overhang(object=$object)` (all paths)

## May invalidate

`at_initial_place($object)`, `away_from_edge($object,*)`

## Policy paths (first match on the bound nouns)

### `slide_to_edge` — when object.flat

1. `policy_045($object)`

## Relations

- Next step: `pick` (`skill_017`) (enables) — pinch the overhang
- Next step: `flip` (`skill_028`) (then) — turn the object over
- Fallback on failure: `approach` (`skill_002`) (repair) — no base pose reaches behind the object
- Is a fallback for: `pick` (`skill_017`) (repair) — a flat object cannot be pinched from the top: push it to the edge by hand, then pick the overhang

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_039`.
