# ZenoBench `skills.py` function inventory

Source: `ZenoBench/zeno_skills/skills.py` at ZenoBench commit `5de7322a3a8575c99878726c7aa46b10f0ca665e` (1,226 lines). This inventory covers **every callable defined in that file**: 36 module-level named functions, three nested named functions, and five anonymous `lambda` expressions, for 44 definitions or expressions total. Line numbers refer to that source revision.

Function definitions are not identical to model-facing Skills. The current nine Contracts expose selected task-level capabilities. Private helpers, grasp and placement strategies, and nested callbacks remain within those capabilities. The distinction is made per function below.

## Navigation and carried-object checks

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `_carry_pose` | 41 | Lift and tuck a held object into a safer travel posture. | Internal helper |
| `check_held` | 70 | Detect whether a carried object has slipped relative to the gripper. | Internal state check |
| `_back_off` | 88 | Reverse from nearby furniture before moving with a held object. | Internal helper |
| `navigate` | 101 | Plan and drive the base to a planar pose, with carry handling. | `skill_001` |
| `_travel_q` | 136 | Select the arm posture used while travelling to a work pose. | Internal helper |
| `_goto_park` | 141 | Navigate to a selected manipulation base pose if needed. | Internal helper |

## Doors and drawers

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `_handle_targets` | 149 | Build approach and grasp poses for an articulated handle. | Internal helper |
| `_ride_check` | 155 | Build a feasibility check for moving with a door or drawer. | Internal helper |
| `_ride_check.check` | 160 | Test footprint and arm clearance across sampled joint positions. | Nested callback |
| `_ride` | 181 | Move the base in a closed loop while pulling an articulated part. | Internal helper |
| `_move_articulated` | 214 | Shared handle grasp, motion, release, and joint-result check. | Internal implementation of `skill_002` and `skill_003` |
| `_move_articulated.score` | 223 | Score candidate work poses by estimated wrist torque. | Nested callback |
| `open_articulated` | 316 | Open an annotated door or drawer to its target joint value. | `skill_002` |
| `close_articulated` | 321 | Close an annotated door or drawer to its target joint value. | `skill_003` |

## Geometry and clearance

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `_yaw` | 327 | Read planar yaw from an object quaternion. | Internal geometry helper |
| `_half_along` | 332 | Project half the footprint of a rotated flat object onto a direction. | Internal geometry helper |
| `_perp` | 339 | Return a perpendicular two-dimensional direction. | Internal geometry helper |
| `_edge_coord` | 343 | Find a support boundary along an outward direction. | Internal geometry helper |
| `_holder_mask` | 349 | Identify obstacle boxes belonging to the furniture holding a support. | Internal geometry helper |
| `_free_beyond` | 357 | Check clearance just beyond a support edge. | Internal geometry helper |
| `_open_edges` | 379 | Find support edges usable for flat-object manipulation. | Internal geometry helper |
| `_free_beyond_hold` | 405 | Check clearance beyond a furniture holder's face. | Internal geometry helper |
| `_overlaps_objects` | 422 | Check whether a candidate volume overlaps other annotated objects. | Internal geometry helper |

## Picking and pushing

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `_grasp_legs` | 435 | Generate staged approach poses for a grasp candidate. | Internal helper |
| `pick` | 441 | Select an annotated grasp strategy and lift an object. | `skill_004` |
| `_pick_pinch` | 458 | Execute a top or rim pinch and check the lifted grasp. | Internal strategy of `pick` |
| `push` | 532 | Push or drag an object across its annotated support; measure displacement. | `skill_005`; also called inside `pick_flat` |
| `pick_flat` | 594 | Push a wide flat object to a free edge, then grasp its overhang; use a floor strategy when needed. | Internal strategy selected by `pick` |
| `_corner_pinch` | 640 | Pinch a flat object lying on the floor from a side/top corner. | Internal strategy of `pick_flat` |
| `_lowest_z` | 717 | Compute the lowest world-space corner of a tilted object box. | Internal geometry helper |
| `_edge_pinch` | 728 | Grasp and lift a flat object's overhanging edge. | Internal strategy of `pick_flat` |

## Placement

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `_yaw_of` | 785 | Extract yaw from a rotation matrix. | Internal geometry helper |
| `place` | 789 | Release a held object into a container or at a supplied point on a support; check the result. | `skill_006` for `in:<container>`; also used by `skill_007` |
| `free_spots` | 949 | Find unoccupied candidate positions on an annotated support. | Internal helper of `place_on` |
| `place_on` | 981 | Search free positions and retry placement on a support. | `skill_007` |
| `place_flat` | 1000 | Place an edge-held flat object over a free support edge, then push it fully onto the surface. | Internal strategy selected by `place` or `place_on` |

## Microwave-specific actions

| Function | Line | Purpose | Library status |
|---|---:|---|---|
| `press_microwave_start` | 1101 | Press the start button and activate configured thermal task state. | `skill_008`; does not itself establish target temperature |
| `cycle_microwave_door` | 1162 | Press the door control, open the powered door for inspection, and reclose it. | `skill_009`; currently uses a fixed inspection pose |
| `cycle_microwave_door.move_hinge` | 1207 | Command and check one powered hinge movement. | Nested helper |

## Anonymous sort-key functions

These five `lambda` expressions are local sorting keys, not independently callable capabilities.

| Expression location | Line | Purpose | Library status |
|---|---:|---|---|
| `_pick_pinch` sort key for refrigerator grasp candidates | 480 | Prefer candidate rim approaches by azimuth and tilt. | Internal `lambda` |
| `_pick_pinch` sort key for other grasp candidates | 484 | Prefer grasp positions near the current base pose. | Internal `lambda` |
| `pick_flat` sort key for edges | 617 | Try edges requiring the least push first. | Internal `lambda` |
| `_corner_pinch` sort key for side candidates | 673 | Try the nearest floor-corner pinch first. | Internal `lambda` |
| `place_flat` sort key for placement candidates | 1036 | Try the best-scored free edge position first. | Internal `lambda` |

## Exposure summary

The current Library exposes nine task-level Contracts: `navigate`, `open_articulated`, `close_articulated`, `pick`, `push`, `place` into a container, `place_on` a support, `press_microwave_start`, and `cycle_microwave_door`. This is a **capability selection**, not a claim that only nine Python functions exist. The placement Contracts deliberately describe different planning goals; both ultimately use the existing placement implementation. The remaining definitions are internal checks, strategies, geometry utilities, or nested callbacks. A future Library revision can expose an internal strategy separately if the model needs to select it independently.
