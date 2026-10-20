---
name: pour-contents
description: "Hold the cup's far lip over a container, turn the cup about that lip up to 90 deg and return it upright; succeeds when at least half of the loose items that were in the cup are inside the target. A rim-held cup tilts away from the pinch; a handle-held cup rolls sideways about the forearm."
---

# Pour contents into a container (`skill_039`)

`pour(source: container_ref, target: container_ref)`

Hold the cup's far lip over a container, turn the cup about that lip up to 90 deg and return it upright; succeeds when at least half of the loose items that were in the cup are inside the target. A rim-held cup tilts away from the pinch; a handle-held cup rolls sideways about the forearm.

## When to use

Loose contents of a held container must go into another container.

## Not to be confused with

- `drop`: drop releases the held object itself; pour tips out its contents.

## Inputs

- `source` (`container_ref`): The held cup or mug with loose items.
- `target` (`container_ref`): The receiving container.

## Outputs

- `moved` (`object_list`): Items now inside the target.

## Applicability

Requires holding(hand=right, object=$source); base_near(place=$target); uncovered(container=$target); not container_empty(container=$source).

## Preconditions (checked on live GT state before moving)

- `holding(hand=right, object=$source)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.
- `base_near(place=$target)` — Base centre within 1.3 m of the place's footprint (inside the room for a room). GT: base_pose, scene_annotation.
- `uncovered(container=$target)` — No lid rests on the container rim. GT: object_pose, container_profile, asset_tags.
- `not container_empty(container=$source)` — No annotated object is inside the container. GT: object_pose, container_profile.

## Postconditions (verified on live GT state)

- `poured_into(source=$source, target=$target)` — At least half of the items that were inside the source are now inside the target. GT: object_pose (before/after), container_profile.
- `holding(hand=right, object=$source)` — The object is in the given gripper: fingers not shut, TCP-to-body distance unchanged since the grasp. GT: gripper_state, finger_joints, object_pose, arm_fk.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `poured_into(source=$source, target=$target)` (all paths)
- `holding(hand=right, object=$source)` (all paths)

## Policy paths (first match on the bound nouns)

### `tilt_over_rim` — when source.is_container

1. `policy_086($source, $target)`

## Relations

- Previous step: `uncover` (`skill_046`) (enables) — food is poured into the opened pot
- Previous step: `shake` (`skill_062`) (enables) — loose contents are poured out
- Next step: `place` (`skill_018`) (enables) — the empty cup is put down
- Next step: `stir` (`skill_038`) (enables) — the poured food is stirred
- Fallback on failure: `uncover` (`skill_046`) (repair, repairs uncovered) — the target has its lid on
- Is a fallback for: `heat` (`skill_043`) (recover) — the food is in a cup, not in the pot on the burner

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_047`.
