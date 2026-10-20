---
name: swap-objects
description: Exchange the positions of two objects on their supports via a free buffer spot.
---

# Swap two objects (`skill_054`)

`swap(a: object_ref, b: object_ref)`

Exchange the positions of two objects on their supports via a free buffer spot.

## When to use

Two objects must exchange places.

## Not to be confused with

- `restore`: swap exchanges two objects.

## Inputs

- `a` (`object_ref`): First object.
- `b` (`object_ref`): Second object.

## Composite skill

Runs these Skill Contracts inside one call: `navigate`, `pick`, `place`.

- One call runs the whole chain of the selected path below; each nested step is a full Skill Contract (preconditions, policy, postconditions on GT state). It counts as a single Contract call.
- The chain includes its own navigation: there is no need to navigate or approach first.
- The first nested step that fails stops the call with SUBSKILL_FAILED; the error names the failed nested action. Nothing is repaired or retried, and steps that already succeeded are not undone, so objects may have moved or still be held.

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `positions_swapped(a=$a, b=$b)` — Each object now rests within 6 cm of the other's starting position on its starting support. GT: object_pose (before/after).
- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `positions_swapped(a=$a, b=$b)` (all paths)
- `hand_empty(hand=right)` (all paths)

## Policy paths (first match on the bound nouns)

### `via_buffer` — when always (default path)

1. `[navigate](destination=$a)`
2. `[pick](object=$a)`
3. `[place](object=$a, receptacle=@a.support, hint_xy=@a.buffer_xy)`
4. `[navigate](destination=$b)`
5. `[pick](object=$b)`
6. `[navigate](destination=@a.support)`
7. `[place](object=$b, receptacle=@a.support, hint_xy=@a.xy)`
8. `[navigate](destination=$a)`
9. `[pick](object=$a)`
10. `[navigate](destination=@b.support)`
11. `[place](object=$a, receptacle=@b.support, hint_xy=@b.xy)`

## Relations

- Next step: `tuck` (`skill_009`) (enables) — the robot drives on
- Alternative: `fetch` (`skill_047`) — only one object needs to move

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_062`.
