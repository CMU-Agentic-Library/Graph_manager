---
name: sweep-objects
description: "Push several objects on one support toward their centroid until they form a cluster (radius 12 cm), without grasping them."
---

# Sweep objects together (`skill_067`)

`sweep(objects: object_list, radius_m: positive_number)`

Push several objects on one support toward their centroid until they form a cluster (radius 12 cm), without grasping them.

## When to use

Several small objects on one support must be gathered into a cluster.

## Not to be confused with

- `arrange`: arrange picks and places; sweep only pushes.
- `collect`: collect puts objects into a container.

## Inputs

- `objects` (`object_list`): Objects on one support.
- `radius_m` (`positive_number`, default 0.12): Cluster radius.

## Applicability

Requires hand_empty(hand=right).

## Preconditions (checked on live GT state before moving)

- `hand_empty(hand=right)` — The given gripper holds nothing. GT: gripper_state.

## Postconditions (verified on live GT state)

- `clustered(objects=$objects, radius_m=$radius_m)` — Every listed object's footprint centre lies within the radius of the group centroid, on one support. GT: object_pose, support_annotation.

## Verifier

after the policy chain, every listed predicate is evaluated on ground-truth simulator state (object poses, joint values, finger gaps, head-camera geometry, thermal state, event log); the node succeeds only if all hold for the selected path:

- `clustered(objects=$objects, radius_m=$radius_m)` (all paths)

## Policy paths (first match on the bound nouns)

### `push_to_centroid` — when always (default path)

1. `policy_109($objects, radius_m=$radius_m)`

## Relations

- Next step: `collect` (`skill_048`) (then) — the cluster is then put into a container
- Alternative: `push` (`skill_029`) — only one object has to move

## Failure

Stop and report the error code and the measured pre- and postconditions. Nothing is retried or repaired automatically.


Paired Contract: `contract_075`.
