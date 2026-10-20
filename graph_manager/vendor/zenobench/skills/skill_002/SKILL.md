---
name: approach-target
description: Park the base where the right arm has a collision-free IK solution at the target's reach pose: 10 cm above an object or support, the handle pre-grasp of a door or drawer, 8 cm in front of a button.
---

# Approach a manipulation target (`skill_002`)

`approach(target: entity_ref, pass_by: pose2d?)`

Park the base where the right arm has a collision-free IK solution at the target's reach pose: 10 cm above an object or support, the handle pre-grasp of a door or drawer, 8 cm in front of a button.

## When to use

Right before a contact action on one specific target.

## Not to be confused with

- `navigate`: navigate goes to a region; approach verifies arm IK for one target.

## Inputs

- `target` (`entity_ref`): The object, support, handle-bearing part or button to reach.
- `pass_by` (`pose2d`, optional): Optional base waypoint: reach toward the target while driving past it.

## Outputs

- `base_pose` (`pose2d`): Base pose at which reachability was verified.

## Applicability

Requires base_near(place=$target).

## Preconditions (checked on live GT state before moving)

- `base_near(place=$target)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `reachable(target=$target)` — From the current base pose the right TCP has a collision-free IK solution 10 cm above the target (handle pre-grasp for doors, 8 cm in front of a button). GT: base_pose, arm_ik, collision_model, object_pose, grasp_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `reachable(target=$target)` (all paths)

## May invalidate

`reachable(*)`, `facing(*)`, `in_view(*)`, `pointing_at(*)`

## Policy paths (first match on the bound nouns)

### `reach_on_the_move` — when args.pass_by

1. `policy_098($target) as reach`
2. `policy_051(#reach.position, #reach.rotation, $pass_by)`
- Extend the arm toward the reach pose while the base follows the given waypoint.

### `park` — when always (default path)

1. `policy_065($target)`

## Relations

- Previous step: `navigate` (`skill_001`) (enables) — a manipulation target is on the destination
- Previous step: `bend` (`skill_007`) (then) — the target was just out of reach
- Previous step: `look` (`skill_011`) (then) — the observed target will be manipulated
- Previous step: `sidestep` (`skill_055`) (then) — the target is now in front of the arm
- Next step: `pick` (`skill_017`) (then) — the target is an object to grasp
- Next step: `open` (`skill_040`) (then) — the target is a door or drawer
- Next step: `press` (`skill_042`) (then) — the target is a button
- Fallback on failure: `navigate` (`skill_001`) (repair, repairs base_near) — no base pose near the current one reaches the target
- Fallback on failure: `bend` (`skill_007`) (recover) — the target is just beyond the arm envelope
- Fallback on failure: `pull` (`skill_030`) (substitute) — the object sits too deep on its support
- Is a fallback for: `pick` (`skill_017`) (recover) — no grasp is reachable from base poses near the current one
- Is a fallback for: `place` (`skill_018`) (recover) — the receptacle is out of reach
- Is a fallback for: `expose` (`skill_031`) (repair) — no base pose reaches behind the object
- Is a fallback for: `open` (`skill_040`) (recover) — the handle is out of reach

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.

- no base pose reaches the target
- IK fails after parking

Paired Contract: `contract_010`.
