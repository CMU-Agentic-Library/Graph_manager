---
name: hide-object
description: Make an object invisible from outside: put it into a container and cover that container with its lid, or put it on a shelf inside a cabinet and close the cabinet.
---

# Hide an object (`skill_070`)

`hide(object: object_ref, receptacle: receptacle_ref, lid: lid_ref?)`

Make an object invisible from outside: put it into a container and cover that container with its lid, or put it on a shelf inside a cabinet and close the cabinet.

## When to use

An object must end up out of sight inside a closed container.

## Not to be confused with

- `collect`: hide also covers the container.

## Inputs

- `object` (`object_ref`): The object to hide.
- `receptacle` (`receptacle_ref`): A lidded container or a cabinet interior shelf.
- `lid` (`lid_ref`, optional): The lid to use for a container.

## Composite skill

Runs these Skill Contracts inside one call: `fetch`, `navigate`, `pick`, `cover`, `open`, `close`, `place`.

- One call runs the whole chain of the selected path below; each nested step is a full Skill Contract (preconditions, policy, postconditions on GT state). It counts as a single Contract call.
- The chain includes its own navigation: there is no need to navigate or approach first.
- The first nested step that fails stops the call with SUBSKILL_FAILED; the error names the failed nested action. Nothing is repaired or retried, and steps that already succeeded are not undone, so objects may have moved or still be held.

## Applicability

Requires hand_empty(hand=right). Depending on the bound nouns, the chosen path also needs: container_with_lid (receptacle.kind == 'object' and args.lid): uncovered(container=$receptacle).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `hidden(object=$object)` — Object is inside a lid-covered container or on a shelf inside a closed cabinet. GT: object_pose, container_profile, articulation_joint, support_annotation.
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `hidden(object=$object)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `container_with_lid` — when receptacle.kind == 'object' and args.lid

1. `[fetch](object=$object, receptacle=$receptacle)`
2. `[navigate](destination=$lid)`
3. `[pick](object=$lid)`
4. `[navigate](destination=$receptacle)`
5. `[cover](container=$receptacle, lid=$lid)`
- extra precondition `uncovered(container=$receptacle)`

### `closed_cabinet` — when receptacle.kind == 'support' and receptacle.category == 'cabinet_inside'

1. `[navigate](destination=@receptacle.appliance)`
2. `[open](articulated=@receptacle.appliance)`
3. `[fetch](object=$object, receptacle=$receptacle)`
4. `[close](articulated=@receptacle.appliance)`

## Relations

- Next step: `tuck` (`skill_009`) (enables) — the robot leaves
- Alternative: `fetch` (`skill_047`) — the object only needs to move

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_078`.
