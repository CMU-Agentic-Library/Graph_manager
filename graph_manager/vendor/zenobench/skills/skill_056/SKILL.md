---
name: wait-duration
description: Do nothing for the given simulated time (an appliance cycle running, an object settling).
---

# Wait for a duration (`skill_056`)

`wait(seconds: positive_number)`

Do nothing for the given simulated time (an appliance cycle running, an object settling).

## When to use

Something must happen over time (cooling, settling) and the robot should not act.

## Not to be confused with

- `heat`: heat waits for a measured temperature; wait for a fixed time.

## Inputs

- `seconds` (`positive_number`, default 5.0): How long to wait.

## Applicability

Always applicable.

## Preconditions (checked on live GT state before moving)

- none

## Postconditions (verified on live GT state)

- `waited(seconds=$seconds)` — At least the given simulated time passed during the Contract. GT: sim_clock.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `waited(seconds=$seconds)` (all paths)

## Policy paths (first match on the bound nouns)

### `idle` — when always (default path)

1. `policy_103($seconds)`

## Relations

- Next step: `open` (`skill_040`) (then) — a cycle finished and the door is opened
- Is a fallback for: `heat` (`skill_043`) (recover) — the food is still below the target when the time budget ends

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_064`.
