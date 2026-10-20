---
name: look-target
description: "Aim the head camera at a target (turning the base if it is outside the head yaw range) and record every annotated object in view as observed."
---

# Look at a target (`skill_011`)

`look(target: entity_ref)`

Aim the head camera at a target (turning the base if it is outside the head yaw range) and record every annotated object in view as observed.

## When to use

A known target must be brought into the head camera view.

## Not to be confused with

- `inspect`: inspect reports a receptacle's contents; look only aims the camera.
- `search`: search visits several places to find an unseen object.

## Inputs

- `target` (`entity_ref`): What to look at.

## Outputs

- `seen` (`object_list`): Objects in the head camera frustum with clear line of sight.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `in_view(target=$target)` — Target point inside the head camera frustum, within 5 m, line of sight not blocked by furniture boxes. GT: base_pose, head_joints, head_fk, collision_model.
- `observed(target=$target)` — The robot saw the target in its head camera during this episode (set by look, search, inspect, explore). GT: robot_memory.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `in_view(target=$target)` (all paths)
- `observed(target=$target)` (all paths)

## May invalidate

`in_view(*)`

## Policy paths (first match on the bound nouns)

### `head_only` — when target.bearing_abs_deg <= 55

1. `policy_068($target)`

### `turn_then_head` — when always (default path)

1. `policy_066($target)`
2. `policy_068($target)`

## Relations

- Previous step: `navigate` (`skill_001`) (then) — the destination must be observed first
- Previous step: `face` (`skill_003`) (then) — the target must be observed
- Previous step: `nod` (`skill_061`) (then) — the robot looks back at a target
- Next step: `approach` (`skill_002`) (then) — the observed target will be manipulated
- Fallback on failure: `navigate` (`skill_001`) (repair) — the line of sight is blocked
- Alternative: `inspect` (`skill_012`) — the target is a receptacle whose contents matter
- Alternative: `point` (`skill_015`) — a gaze is enough to indicate the target

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_019`.
