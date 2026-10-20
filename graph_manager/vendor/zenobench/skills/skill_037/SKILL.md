---
name: wipe-surface
description: Press a held sponge on a support and sweep a 30 cm strip twice; succeeds when the sponge stayed in contact over at least half of the strip.
---

# Wipe a surface (`skill_037`)

`wipe(surface: support_ref, tool: tool_ref)`

Press a held sponge on a support and sweep a 30 cm strip twice; succeeds when the sponge stayed in contact over at least half of the strip.

## When to use

A surface must be wiped with a held sponge or cloth.

## Not to be confused with

- `sweep`: wipe uses a held tool on the surface itself.

## Inputs

- `surface` (`support_ref`): The support to clean.
- `tool` (`tool_ref`): The held wiping tool (sponge).

## Outputs

- `coverage` (`number`): Fraction of the strip wiped in contact.

## Applicability

Requires holding(hand=right, object=$tool); base_near(place=$surface).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$surface)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.

## Postconditions (verified on live GT state)

- `wiped(support=$surface)` — A held wiping tool stayed in contact with at least 50 % of the requested strip of the support. GT: robot_memory (tool-bottom contact samples).
- `holding(hand=right, object=$tool)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `wiped(support=$surface)` (all paths)
- `holding(hand=right, object=$tool)` (all paths)

## Policy paths (first match on the bound nouns)

### `sponge_strip` — when 'wiping_tool' in tool.tags

1. `policy_084($tool, $surface)`

## Relations

- Previous step: `clear` (`skill_050`) (then) — the cleared surface is wiped
- Next step: `place` (`skill_018`) (enables) — the sponge is put back
- Fallback on failure: `clear` (`skill_050`) (recover) — objects cover the surface

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_045`.
